/**
 * Organization Settings Modals
 * CRUD modals for GST, Banks, Financial Years, and Document Series
 */

import { useState } from 'react';
import Modal from '@/components/common/Modal';
import { useToast } from '@/contexts/ToastContext';
import organizationService from '@/services/api/organizationService';
import type {
  OrganizationGST,
  OrganizationGSTCreate,
  OrganizationBankAccount,
  OrganizationBankAccountCreate,
  OrganizationFinancialYear,
  OrganizationFinancialYearCreate,
  OrganizationDocumentSeries,
  OrganizationDocumentSeriesCreate,
} from '@/types/settings';

// ==================== GST Modal ====================

interface GSTModalProps {
  isOpen: boolean;
  onClose: () => void;
  organizationId: string;
  gst?: OrganizationGST;
  onSuccess: () => void;
}

export function GSTModal({ isOpen, onClose, organizationId, gst, onSuccess }: GSTModalProps) {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState<OrganizationGSTCreate>({
    organization_id: organizationId,
    gstin: gst?.gstin || '',
    state: gst?.state || '',
    registration_date: gst?.registration_date || '',
    is_primary: gst?.is_primary ?? false,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (gst) {
        await organizationService.updateGST(gst.id, formData);
        toast.success('GST details updated successfully');
      } else {
        await organizationService.createGST(formData);
        toast.success('GST details added successfully');
      }
      onSuccess();
      onClose();
    } catch (error: any) {
      toast.error(error.message || 'Failed to save GST details');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={gst ? 'Edit GST Details' : 'Add GST Details'} size="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-pearl-300 mb-2">
            GSTIN <span className="text-mars-400">*</span>
          </label>
          <input
            type="text"
            required
            maxLength={15}
            value={formData.gstin}
            onChange={(e) => setFormData({ ...formData, gstin: e.target.value.toUpperCase() })}
            placeholder="22AAAAA0000A1Z5"
            className="w-full px-3 py-2 bg-pearl-800/50 border border-pearl-700/30 rounded-lg text-pearl-100 placeholder-pearl-500 focus:outline-none focus:ring-2 focus:ring-sun-500"
          />
          <p className="text-xs text-pearl-500 mt-1">15 characters GST Identification Number</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-pearl-300 mb-2">
            State <span className="text-mars-400">*</span>
          </label>
          <input
            type="text"
            required
            value={formData.state}
            onChange={(e) => setFormData({ ...formData, state: e.target.value })}
            placeholder="Maharashtra"
            className="w-full px-3 py-2 bg-pearl-800/50 border border-pearl-700/30 rounded-lg text-pearl-100 placeholder-pearl-500 focus:outline-none focus:ring-2 focus:ring-sun-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-pearl-300 mb-2">
            Registration Date <span className="text-mars-400">*</span>
          </label>
          <input
            type="date"
            required
            value={formData.registration_date}
            onChange={(e) => setFormData({ ...formData, registration_date: e.target.value })}
            className="w-full px-3 py-2 bg-pearl-800/50 border border-pearl-700/30 rounded-lg text-pearl-100 focus:outline-none focus:ring-2 focus:ring-sun-500"
          />
        </div>

        <div className="flex items-center">
          <input
            type="checkbox"
            id="is_primary"
            checked={formData.is_primary}
            onChange={(e) => setFormData({ ...formData, is_primary: e.target.checked })}
            className="w-4 h-4 text-sun-500 bg-pearl-800/50 border-pearl-700/30 rounded focus:ring-sun-500"
          />
          <label htmlFor="is_primary" className="ml-2 text-sm text-pearl-300">
            Primary GST
          </label>
        </div>

        <div className="flex justify-end space-x-3 pt-4">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-pearl-800/50 text-pearl-300 rounded-lg hover:bg-pearl-800 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-gradient-to-r from-saturn-500 to-sun-500 text-white rounded-lg hover:from-saturn-600 hover:to-sun-600 disabled:opacity-50 transition-all"
          >
            {loading ? 'Saving...' : gst ? 'Update' : 'Add'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

// ==================== Bank Account Modal ====================

interface BankAccountModalProps {
  isOpen: boolean;
  onClose: () => void;
  organizationId: string;
  account?: OrganizationBankAccount;
  onSuccess: () => void;
}

export function BankAccountModal({ isOpen, onClose, organizationId, account, onSuccess }: BankAccountModalProps) {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState<OrganizationBankAccountCreate>({
    organization_id: organizationId,
    bank_name: account?.bank_name || '',
    account_number: account?.account_number || '',
    ifsc_code: account?.ifsc_code || '',
    branch: account?.branch || '',
    account_type: account?.account_type || 'current',
    is_primary: account?.is_primary ?? false,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (account) {
        await organizationService.updateBankAccount(account.id, formData);
        toast.success('Bank account updated successfully');
      } else {
        await organizationService.createBankAccount(formData);
        toast.success('Bank account added successfully');
      }
      onSuccess();
      onClose();
    } catch (error: any) {
      toast.error(error.message || 'Failed to save bank account');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={account ? 'Edit Bank Account' : 'Add Bank Account'} size="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-pearl-300 mb-2">
            Bank Name <span className="text-mars-400">*</span>
          </label>
          <input
            type="text"
            required
            value={formData.bank_name}
            onChange={(e) => setFormData({ ...formData, bank_name: e.target.value })}
            placeholder="HDFC Bank"
            className="w-full px-3 py-2 bg-pearl-800/50 border border-pearl-700/30 rounded-lg text-pearl-100 placeholder-pearl-500 focus:outline-none focus:ring-2 focus:ring-sun-500"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-pearl-300 mb-2">
              Account Number <span className="text-mars-400">*</span>
            </label>
            <input
              type="text"
              required
              value={formData.account_number}
              onChange={(e) => setFormData({ ...formData, account_number: e.target.value })}
              placeholder="00001234567890"
              className="w-full px-3 py-2 bg-pearl-800/50 border border-pearl-700/30 rounded-lg text-pearl-100 placeholder-pearl-500 focus:outline-none focus:ring-2 focus:ring-sun-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-pearl-300 mb-2">
              IFSC Code <span className="text-mars-400">*</span>
            </label>
            <input
              type="text"
              required
              maxLength={11}
              value={formData.ifsc_code}
              onChange={(e) => setFormData({ ...formData, ifsc_code: e.target.value.toUpperCase() })}
              placeholder="HDFC0001234"
              className="w-full px-3 py-2 bg-pearl-800/50 border border-pearl-700/30 rounded-lg text-pearl-100 placeholder-pearl-500 focus:outline-none focus:ring-2 focus:ring-sun-500"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-pearl-300 mb-2">
            Branch <span className="text-mars-400">*</span>
          </label>
          <input
            type="text"
            required
            value={formData.branch}
            onChange={(e) => setFormData({ ...formData, branch: e.target.value })}
            placeholder="Mumbai Main"
            className="w-full px-3 py-2 bg-pearl-800/50 border border-pearl-700/30 rounded-lg text-pearl-100 placeholder-pearl-500 focus:outline-none focus:ring-2 focus:ring-sun-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-pearl-300 mb-2">
            Account Type <span className="text-mars-400">*</span>
          </label>
          <select
            required
            value={formData.account_type}
            onChange={(e) => setFormData({ ...formData, account_type: e.target.value as 'savings' | 'current' })}
            className="w-full px-3 py-2 bg-pearl-800/50 border border-pearl-700/30 rounded-lg text-pearl-100 focus:outline-none focus:ring-2 focus:ring-sun-500"
          >
            <option value="current">Current</option>
            <option value="savings">Savings</option>
          </select>
        </div>

        <div className="flex items-center">
          <input
            type="checkbox"
            id="is_primary_bank"
            checked={formData.is_primary}
            onChange={(e) => setFormData({ ...formData, is_primary: e.target.checked })}
            className="w-4 h-4 text-sun-500 bg-pearl-800/50 border-pearl-700/30 rounded focus:ring-sun-500"
          />
          <label htmlFor="is_primary_bank" className="ml-2 text-sm text-pearl-300">
            Primary Bank Account
          </label>
        </div>

        <div className="flex justify-end space-x-3 pt-4">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-pearl-800/50 text-pearl-300 rounded-lg hover:bg-pearl-800 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-gradient-to-r from-saturn-500 to-sun-500 text-white rounded-lg hover:from-saturn-600 hover:to-sun-600 disabled:opacity-50 transition-all"
          >
            {loading ? 'Saving...' : account ? 'Update' : 'Add'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

// ==================== Financial Year Modal ====================

interface FinancialYearModalProps {
  isOpen: boolean;
  onClose: () => void;
  organizationId: string;
  year?: OrganizationFinancialYear;
  onSuccess: () => void;
}

export function FinancialYearModal({ isOpen, onClose, organizationId, year, onSuccess }: FinancialYearModalProps) {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState<OrganizationFinancialYearCreate>({
    organization_id: organizationId,
    year_name: year?.year_name || '',
    start_date: year?.start_date || '',
    end_date: year?.end_date || '',
    is_current: year?.is_current ?? false,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (year) {
        await organizationService.updateFinancialYear(year.id, formData);
        toast.success('Financial year updated successfully');
      } else {
        await organizationService.createFinancialYear(formData);
        toast.success('Financial year added successfully');
      }
      onSuccess();
      onClose();
    } catch (error: any) {
      toast.error(error.message || 'Failed to save financial year');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={year ? 'Edit Financial Year' : 'Add Financial Year'} size="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-pearl-300 mb-2">
            Year Name <span className="text-mars-400">*</span>
          </label>
          <input
            type="text"
            required
            value={formData.year_name}
            onChange={(e) => setFormData({ ...formData, year_name: e.target.value })}
            placeholder="FY 2024-25"
            className="w-full px-3 py-2 bg-pearl-800/50 border border-pearl-700/30 rounded-lg text-pearl-100 placeholder-pearl-500 focus:outline-none focus:ring-2 focus:ring-sun-500"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-pearl-300 mb-2">
              Start Date <span className="text-mars-400">*</span>
            </label>
            <input
              type="date"
              required
              value={formData.start_date}
              onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-800/50 border border-pearl-700/30 rounded-lg text-pearl-100 focus:outline-none focus:ring-2 focus:ring-sun-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-pearl-300 mb-2">
              End Date <span className="text-mars-400">*</span>
            </label>
            <input
              type="date"
              required
              value={formData.end_date}
              onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-800/50 border border-pearl-700/30 rounded-lg text-pearl-100 focus:outline-none focus:ring-2 focus:ring-sun-500"
            />
          </div>
        </div>

        <div className="flex items-center">
          <input
            type="checkbox"
            id="is_current_fy"
            checked={formData.is_current}
            onChange={(e) => setFormData({ ...formData, is_current: e.target.checked })}
            className="w-4 h-4 text-sun-500 bg-pearl-800/50 border-pearl-700/30 rounded focus:ring-sun-500"
          />
          <label htmlFor="is_current_fy" className="ml-2 text-sm text-pearl-300">
            Current Financial Year
          </label>
        </div>

        <div className="flex justify-end space-x-3 pt-4">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-pearl-800/50 text-pearl-300 rounded-lg hover:bg-pearl-800 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-gradient-to-r from-saturn-500 to-sun-500 text-white rounded-lg hover:from-saturn-600 hover:to-sun-600 disabled:opacity-50 transition-all"
          >
            {loading ? 'Saving...' : year ? 'Update' : 'Add'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

// ==================== Document Series Modal ====================

interface DocumentSeriesModalProps {
  isOpen: boolean;
  onClose: () => void;
  organizationId: string;
  series?: OrganizationDocumentSeries;
  onSuccess: () => void;
}

export function DocumentSeriesModal({ isOpen, onClose, organizationId, series, onSuccess }: DocumentSeriesModalProps) {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState<OrganizationDocumentSeriesCreate>({
    organization_id: organizationId,
    document_type: series?.document_type || 'invoice',
    prefix: series?.prefix || '',
    current_number: series?.current_number || 1,
    padding_length: series?.padding_length || 4,
    suffix: series?.suffix || null,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (series) {
        await organizationService.updateDocumentSeries(series.id, formData);
        toast.success('Document series updated successfully');
      } else {
        await organizationService.createDocumentSeries(formData);
        toast.success('Document series added successfully');
      }
      onSuccess();
      onClose();
    } catch (error: any) {
      toast.error(error.message || 'Failed to save document series');
    } finally {
      setLoading(false);
    }
  };

  const previewFormat = `${formData.prefix}${String(formData.current_number).padStart(formData.padding_length, '0')}${formData.suffix || ''}`;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={series ? 'Edit Document Series' : 'Add Document Series'} size="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-pearl-300 mb-2">
            Document Type <span className="text-mars-400">*</span>
          </label>
          <select
            required
            value={formData.document_type}
            onChange={(e) => setFormData({ ...formData, document_type: e.target.value as any })}
            className="w-full px-3 py-2 bg-pearl-800/50 border border-pearl-700/30 rounded-lg text-pearl-100 focus:outline-none focus:ring-2 focus:ring-sun-500"
          >
            <option value="invoice">Invoice</option>
            <option value="purchase_order">Purchase Order</option>
            <option value="quotation">Quotation</option>
            <option value="delivery_note">Delivery Note</option>
            <option value="receipt">Receipt</option>
          </select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-pearl-300 mb-2">
              Prefix <span className="text-mars-400">*</span>
            </label>
            <input
              type="text"
              required
              value={formData.prefix}
              onChange={(e) => setFormData({ ...formData, prefix: e.target.value })}
              placeholder="INV-"
              className="w-full px-3 py-2 bg-pearl-800/50 border border-pearl-700/30 rounded-lg text-pearl-100 placeholder-pearl-500 focus:outline-none focus:ring-2 focus:ring-sun-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-pearl-300 mb-2">
              Suffix
            </label>
            <input
              type="text"
              value={formData.suffix || ''}
              onChange={(e) => setFormData({ ...formData, suffix: e.target.value || null })}
              placeholder="/24"
              className="w-full px-3 py-2 bg-pearl-800/50 border border-pearl-700/30 rounded-lg text-pearl-100 placeholder-pearl-500 focus:outline-none focus:ring-2 focus:ring-sun-500"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-pearl-300 mb-2">
              Starting Number <span className="text-mars-400">*</span>
            </label>
            <input
              type="number"
              required
              min="1"
              value={formData.current_number}
              onChange={(e) => setFormData({ ...formData, current_number: parseInt(e.target.value) })}
              className="w-full px-3 py-2 bg-pearl-800/50 border border-pearl-700/30 rounded-lg text-pearl-100 focus:outline-none focus:ring-2 focus:ring-sun-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-pearl-300 mb-2">
              Padding Length <span className="text-mars-400">*</span>
            </label>
            <input
              type="number"
              required
              min="1"
              max="10"
              value={formData.padding_length}
              onChange={(e) => setFormData({ ...formData, padding_length: parseInt(e.target.value) })}
              className="w-full px-3 py-2 bg-pearl-800/50 border border-pearl-700/30 rounded-lg text-pearl-100 focus:outline-none focus:ring-2 focus:ring-sun-500"
            />
          </div>
        </div>

        <div className="p-3 bg-sun-500/10 border border-sun-500/30 rounded-lg">
          <p className="text-sm text-pearl-300">
            <span className="text-pearl-500">Preview:</span>{' '}
            <span className="text-sun-400 font-mono font-semibold">{previewFormat}</span>
          </p>
        </div>

        <div className="flex justify-end space-x-3 pt-4">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-pearl-800/50 text-pearl-300 rounded-lg hover:bg-pearl-800 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-gradient-to-r from-saturn-500 to-sun-500 text-white rounded-lg hover:from-saturn-600 hover:to-sun-600 disabled:opacity-50 transition-all"
          >
            {loading ? 'Saving...' : series ? 'Update' : 'Add'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
