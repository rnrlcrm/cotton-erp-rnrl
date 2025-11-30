# Disaster Recovery Runbook - Google Cloud Platform

**Last Updated**: November 29, 2025  
**System**: Cotton ERP  
**Platform**: Google Cloud Platform  
**RTO**: 4 hours  
**RPO**: 15 minutes

## Table of Contents
1. [Emergency Contacts](#emergency-contacts)
2. [Backup Strategy](#backup-strategy)
3. [Recovery Procedures](#recovery-procedures)
4. [Failover Procedures](#failover-procedures)
5. [Testing Schedule](#testing-schedule)

---

## Emergency Contacts

### Primary On-Call
- **Role**: DevOps Lead
- **Contact**: [TO BE FILLED]
- **Backup**: [TO BE FILLED]

### GCP Support
- **Support Level**: Premium Support (24/7)
- **Phone**: [TO BE FILLED]
- **Case Portal**: https://console.cloud.google.com/support

---

## Backup Strategy

### Database Backups (Cloud SQL)

**Automated Backups**:
- **Frequency**: Every 4 hours
- **Retention**: 30 days
- **Location**: Same region + cross-region replica
- **Type**: Point-in-time recovery enabled

```bash
# Verify backup status
gcloud sql backups list --instance=cotton-erp-db

# Create manual backup
gcloud sql backups create --instance=cotton-erp-db \
  --description="Manual backup before deployment"
```

**Binary Logs**:
- **Retention**: 7 days
- **Purpose**: Point-in-time recovery (RPO: 15 minutes)

### Application Backups

**Container Images**:
- **Registry**: Google Artifact Registry
- **Retention**: All production tags retained indefinitely
- **Location**: `us-central1-docker.pkg.dev/[PROJECT]/cotton-erp`

**Configuration**:
- **Storage**: Cloud Storage bucket `gs://cotton-erp-config-backup`
- **Frequency**: On every change (versioned)
- **Retention**: 90 days

```bash
# Backup current configuration
gsutil -m cp -r backend/configs gs://cotton-erp-config-backup/$(date +%Y%m%d)/
```

### Event Store Backups

**Critical for 15-year architecture**:
- Events are immutable audit trail
- MUST be backed up separately from operational data

```bash
# Export events table
gcloud sql export csv cotton-erp-db \
  gs://cotton-erp-event-store-backup/events-$(date +%Y%m%d).csv \
  --database=cotton_prod \
  --query="SELECT * FROM events WHERE created_at >= NOW() - INTERVAL '1 DAY'"
```

**Frequency**: Daily  
**Retention**: Permanent (archive to Coldline after 1 year)

---

## Recovery Procedures

### Scenario 1: Database Corruption

**Symptoms**:
- Data inconsistencies
- Failed integrity checks
- Application errors

**Recovery Steps**:

1. **Assess Damage**
   ```bash
   # Connect to database
   gcloud sql connect cotton-erp-db --user=postgres
   
   # Run integrity checks
   SELECT * FROM pg_stat_database_conflicts;
   ```

2. **Stop Application Traffic**
   ```bash
   # Scale down Cloud Run services
   gcloud run services update cotton-erp-backend \
     --region=us-central1 \
     --max-instances=0
   ```

3. **Identify Last Good Backup**
   ```bash
   # List recent backups
   gcloud sql backups list --instance=cotton-erp-db --limit=10
   ```

4. **Restore from Backup**
   ```bash
   # Create new instance from backup
   gcloud sql instances create cotton-erp-db-recovery \
     --backup=[BACKUP_ID] \
     --region=us-central1 \
     --tier=db-n1-highmem-4
   
   # Or restore to existing instance (DESTRUCTIVE)
   gcloud sql backups restore [BACKUP_ID] \
     --backup-instance=cotton-erp-db \
     --backup-id=[BACKUP_ID]
   ```

5. **Verify Data Integrity**
   ```bash
   # Run verification script
   python scripts/verify_data_integrity.py --instance=cotton-erp-db-recovery
   ```

6. **Update DNS/Connection Strings**
   ```bash
   # Update Secret Manager with new connection string
   echo -n "[NEW_CONNECTION_STRING]" | \
     gcloud secrets versions add DATABASE_URL --data-file=-
   ```

7. **Resume Traffic**
   ```bash
   # Scale up Cloud Run
   gcloud run services update cotton-erp-backend \
     --region=us-central1 \
     --max-instances=100
   ```

**RTO**: 2 hours  
**RPO**: Up to 4 hours (last automatic backup)

---

### Scenario 2: Complete Region Failure

**Symptoms**:
- All GCP services in region unavailable
- DNS resolution fails
- 100% error rate

**Recovery Steps**:

1. **Activate Cross-Region Replica**
   ```bash
   # Promote read replica to master
   gcloud sql instances promote-replica cotton-erp-db-replica \
     --region=us-east1
   ```

2. **Deploy Application to Secondary Region**
   ```bash
   # Deploy Cloud Run service in secondary region
   gcloud run deploy cotton-erp-backend \
     --region=us-east1 \
     --image=us-central1-docker.pkg.dev/[PROJECT]/cotton-erp/backend:latest
   ```

3. **Update Global Load Balancer**
   ```bash
   # Update backend service to use secondary region
   gcloud compute backend-services update cotton-erp-backend \
     --global \
     --remove-backends=[PRIMARY_NEG] \
     --add-backends=[SECONDARY_NEG]
   ```

4. **Verify Application Health**
   ```bash
   # Check readiness
   curl https://[SECONDARY_REGION_URL]/ready
   ```

5. **Monitor for Primary Region Recovery**
   - GCP Status Dashboard: https://status.cloud.google.com
   - Set up alerts for region recovery

**RTO**: 4 hours  
**RPO**: 15 minutes (binary log replication)

---

### Scenario 3: Accidental Data Deletion

**Symptoms**:
- User reports missing data
- Audit logs show DELETE operations
- Data not in current database

**Recovery Steps**:

1. **Identify Deletion Time**
   ```sql
   -- Query event store for deletion events
   SELECT * FROM events 
   WHERE event_type LIKE '%.deleted' 
   AND timestamp > NOW() - INTERVAL '24 HOURS'
   ORDER BY timestamp DESC;
   ```

2. **Point-in-Time Recovery**
   ```bash
   # Clone database to point before deletion
   gcloud sql instances clone cotton-erp-db \
     cotton-erp-db-recovery \
     --point-in-time="2025-11-29T14:30:00Z"
   ```

3. **Extract Deleted Data**
   ```bash
   # Export specific records
   gcloud sql export csv cotton-erp-db-recovery \
     gs://cotton-erp-recovery/deleted-records.csv \
     --database=cotton_prod \
     --query="SELECT * FROM [TABLE] WHERE id IN ('[IDS]')"
   ```

4. **Re-import to Production**
   ```bash
   # Import via application API (maintains audit trail)
   python scripts/reimport_data.py \
     --source=gs://cotton-erp-recovery/deleted-records.csv \
     --dry-run  # Test first
   
   python scripts/reimport_data.py \
     --source=gs://cotton-erp-recovery/deleted-records.csv
   ```

**RTO**: 1 hour  
**RPO**: 0 (exact point-in-time)

---

## Failover Procedures

### Planned Maintenance Failover

**Use Case**: Region migration, major upgrades

1. **Enable Maintenance Mode**
   ```bash
   # Set environment variable
   gcloud run services update cotton-erp-backend \
     --update-env-vars MAINTENANCE_MODE=true
   ```

2. **Drain Active Connections**
   ```bash
   # Wait for active requests to complete (max 5 minutes)
   sleep 300
   ```

3. **Perform Maintenance**
   - Database upgrade
   - Schema migration
   - Infrastructure changes

4. **Disable Maintenance Mode**
   ```bash
   gcloud run services update cotton-erp-backend \
     --remove-env-vars MAINTENANCE_MODE
   ```

---

## Testing Schedule

### Monthly DR Tests

**First Monday of Each Month**:
- Restore latest backup to test environment
- Verify data integrity
- Test application startup
- Document any issues

```bash
# Automated monthly test
gcloud scheduler jobs create http dr-test-monthly \
  --schedule="0 9 1 * *" \
  --uri="https://[INTERNAL_URL]/admin/dr-test" \
  --http-method=POST
```

### Quarterly Failover Tests

**First Monday of Q1, Q2, Q3, Q4**:
- Full regional failover
- Promote replica to primary
- Update load balancers
- Validate all services
- Measure actual RTO/RPO

### Annual DR Drill

**Once Per Year**:
- Simulate complete region failure
- Full team participation
- Document lessons learned
- Update runbooks

---

## Monitoring & Alerts

### Critical Alerts

**Database Health**:
```bash
# Create alert policy
gcloud alpha monitoring policies create \
  --notification-channels=[CHANNEL_ID] \
  --display-name="Database CPU > 80%" \
  --condition-threshold-value=0.8 \
  --condition-threshold-duration=300s \
  --aggregation-aligner=ALIGN_MEAN
```

**Backup Failures**:
- Alert if no backup in 6 hours
- Alert if backup size drops >50%

**Application Health**:
- Error rate > 1%
- Latency p99 > 2 seconds
- Instance crash loop

---

## Post-Incident Review

After any DR event, complete within 48 hours:

1. **Timeline Documentation**
   - First alert time
   - Response initiated
   - Services restored
   - Full resolution

2. **RTO/RPO Verification**
   - Actual vs target RTO
   - Data loss assessment
   - Customer impact

3. **Runbook Updates**
   - What worked
   - What didn't
   - Improvements needed

4. **Team Debrief**
   - Blameless postmortem
   - Action items
   - Training gaps

---

## Appendix: Quick Reference Commands

```bash
# Check database status
gcloud sql instances describe cotton-erp-db

# List backups
gcloud sql backups list --instance=cotton-erp-db

# Restore backup
gcloud sql backups restore [BACKUP_ID] --backup-instance=cotton-erp-db

# Promote replica
gcloud sql instances promote-replica cotton-erp-db-replica

# Check Cloud Run status
gcloud run services describe cotton-erp-backend --region=us-central1

# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit=50

# Emergency scale down
gcloud run services update cotton-erp-backend --max-instances=0
```

---

**Document Control**:
- Version: 1.0
- Owner: DevOps Team
- Review Frequency: Quarterly
- Next Review: February 2026
