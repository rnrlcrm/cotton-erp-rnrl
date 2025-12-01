"""
Partner Scheduled Jobs

Background jobs for partner module:
- Daily KYC reminder checks
- Auto-suspend expired KYC partners
- Monthly risk score recalculation

These jobs should be registered with Celery or APScheduler
"""

from __future__ import annotations

from datetime import datetime, timedelta
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters.email.service import EmailService
from backend.adapters.sms.service import SMSService
from backend.modules.partners.models import BusinessPartner
from backend.modules.partners.notifications import check_and_send_kyc_reminders
from backend.core.events.emitter import EventEmitter
from backend.modules.partners.events import PartnerSuspendedEvent, KYCExpiredEvent


async def daily_kyc_reminder_job(
    db: AsyncSession,
    email_service: EmailService,
    sms_service: SMSService
) -> dict:
    """
    Daily job to check and send KYC renewal reminders
    
    Should run daily at 9:00 AM
    
    Usage with APScheduler:
    ```python
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        daily_kyc_reminder_job,
        'cron',
        hour=9,
        minute=0,
        args=[db, email_service, sms_service]
    )
    scheduler.start()
    ```
    
    Usage with Celery:
    ```python
    from celery import Celery
    from celery.schedules import crontab
    
    app = Celery('cotton_erp')
    
    @app.task
    def kyc_reminder_task():
        # Get DB session, services
        asyncio.run(daily_kyc_reminder_job(db, email_service, sms_service))
    
    app.conf.beat_schedule = {
        'kyc-reminders-daily': {
            'task': 'kyc_reminder_task',
            'schedule': crontab(hour=9, minute=0),
        },
    }
    ```
    """
    reminders_sent = await check_and_send_kyc_reminders(db, email_service, sms_service)
    
    return {
        "job": "daily_kyc_reminder",
        "executed_at": datetime.utcnow().isoformat(),
        "reminders_sent": reminders_sent
    }


async def auto_suspend_expired_kyc_job(
    db: AsyncSession,
    emitter: EventEmitter,
    auto_suspend_enabled: bool = False  # CONFIGURABLE - default is NO auto-suspend
) -> dict:
    """
    Check for expired KYC and optionally auto-suspend
    
    IMPORTANT: By default, this only sends notifications.
    Set auto_suspend_enabled=True to actually suspend partners.
    
    Should run daily at 00:01 AM
    
    Returns: Number of partners checked and optionally suspended
    """
    now = datetime.utcnow()
    
    # Find partners with expired KYC
    query = select(BusinessPartner).where(
        BusinessPartner.is_deleted == False,
        BusinessPartner.status == "active",
        BusinessPartner.kyc_expiry_date < now
    )
    
    result = await db.execute(query)
    expired_partners = result.scalars().all()
    
    suspended_count = 0
    
    for partner in expired_partners:
        # Always emit KYC expired event (triggers notification)
        await emitter.emit(KYCExpiredEvent(
            partner_id=partner.id,
            organization_id=partner.organization_id,
            partner_name=partner.legal_business_name,
            expired_at=now,
            last_kyc_date=partner.kyc_expiry_date
        ))
        
        # Only suspend if enabled
        if auto_suspend_enabled:
            partner.status = "suspended"
            partner.updated_at = now
            
            await emitter.emit(PartnerSuspendedEvent(
                partner_id=partner.id,
                organization_id=partner.organization_id,
                reason="KYC expired - auto-suspended",
                suspended_at=now
            ))
            
            suspended_count += 1
    
    await db.commit()
    
    return {
        "job": "check_expired_kyc",
        "executed_at": now.isoformat(),
        "partners_with_expired_kyc": len(expired_partners),
        "partners_suspended": suspended_count if auto_suspend_enabled else 0,
        "auto_suspend_enabled": auto_suspend_enabled
    }


async def monthly_risk_recalculation_job(
    db: AsyncSession
) -> dict:
    """
    Recalculate risk scores for all active partners monthly
    
    Should run on 1st of each month at 00:00
    
    This helps identify partners whose risk profile has changed
    """
    from backend.modules.partners.partner_services import RiskScoringService
    
    # Get all active partners
    query = select(BusinessPartner).where(
        BusinessPartner.is_deleted == False,
        BusinessPartner.status == "active"
    )
    
    result = await db.execute(query)
    partners = result.scalars().all()
    
    risk_service = RiskScoringService(db)
    recalculated_count = 0
    risk_increased_count = 0
    
    for partner in partners:
        old_score = partner.risk_score or 0
        
        # Recalculate risk
        risk_result = await risk_service.calculate_risk_score(partner.id)
        
        new_score = risk_result["risk_score"]
        
        # Update if changed significantly (>10 points)
        if abs(new_score - old_score) > 10:
            partner.risk_score = new_score
            partner.risk_category = risk_result["risk_category"]
            partner.risk_assessment = risk_result
            partner.last_risk_assessment_at = datetime.utcnow()
            
            if new_score > old_score:
                risk_increased_count += 1
            
            recalculated_count += 1
    
    await db.commit()
    
    return {
        "job": "monthly_risk_recalculation",
        "executed_at": datetime.utcnow().isoformat(),
        "partners_checked": len(partners),
        "scores_updated": recalculated_count,
        "risk_increased": risk_increased_count
    }


# Job registration helper
def register_partner_jobs(scheduler, db, email_service, sms_service, emitter):
    """
    Register all partner jobs with scheduler
    
    Example with APScheduler:
    ```python
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    
    scheduler = AsyncIOScheduler()
    register_partner_jobs(scheduler, db, email_service, sms_service, emitter)
    scheduler.start()
    ```
    """
    
    # Daily KYC reminders at 9 AM
    scheduler.add_job(
        daily_kyc_reminder_job,
        'cron',
        hour=9,
        minute=0,
        args=[db, email_service, sms_service],
        id='partner_kyc_reminders',
        name='Daily KYC Renewal Reminders',
        replace_existing=True
    )
    
    # Daily check for expired KYC at 00:01 AM - DOES NOT auto-suspend by default
    # Set args=[db, emitter, True] to enable auto-suspend
    scheduler.add_job(
        auto_suspend_expired_kyc_job,
        'cron',
        hour=0,
        minute=1,
        args=[db, emitter, False],  # False = only notify, True = auto-suspend
        id='partner_check_expired_kyc',
        name='Check Expired KYC (No Auto-Suspend)',
        replace_existing=True
    )
    
    # Monthly risk recalculation on 1st at midnight
    scheduler.add_job(
        monthly_risk_recalculation_job,
        'cron',
        day=1,
        hour=0,
        minute=0,
        args=[db],
        id='partner_risk_recalc',
        name='Monthly Risk Score Recalculation',
        replace_existing=True
    )
