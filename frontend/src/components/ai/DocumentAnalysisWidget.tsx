/**
 * Document Analysis Widget
 * AI-powered document analysis for contracts, invoices, and quality reports
 */

import { useState } from 'react';
import {
  DocumentTextIcon,
  SparklesIcon,
  XMarkIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';

interface DocumentAnalysisWidgetProps {
  onClose?: () => void;
}

interface AnalysisResult {
  analysis: string;
  insights: string[];
  metadata: {
    document_type: string;
    analysis_type: string;
    word_count: number;
  };
}

export default function DocumentAnalysisWidget({ onClose }: DocumentAnalysisWidgetProps) {
  const [documentText, setDocumentText] = useState('');
  const [documentType, setDocumentType] = useState<'contract' | 'invoice' | 'quality_report'>('contract');
  const [analysisType, setAnalysisType] = useState<'summary' | 'risks' | 'compliance' | 'trends'>('summary');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const analyzeDocument = async () => {
    if (!documentText.trim()) {
      setError('Please enter document text to analyze');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/ai/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({
          document_text: documentText,
          document_type: documentType,
          analysis_type: analysisType,
        }),
      });

      if (!response.ok) {
        throw new Error('Analysis failed');
      }

      const data = await response.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'Failed to analyze document');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-space-900 via-space-800 to-saturn-900">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-pearl-700/30">
        <div className="flex items-center space-x-2">
          <DocumentTextIcon className="w-5 h-5 text-sun-400" />
          <h3 className="font-semibold text-pearl-100">Document Analysis</h3>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 hover:bg-pearl-700/30 rounded transition-colors"
          >
            <XMarkIcon className="w-5 h-5 text-pearl-400" />
          </button>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Document Type */}
        <div>
          <label className="block text-sm font-medium text-pearl-300 mb-2">
            Document Type
          </label>
          <select
            value={documentType}
            onChange={(e) => setDocumentType(e.target.value as any)}
            className="w-full px-3 py-2 bg-pearl-800/50 border border-pearl-700/30 rounded-lg text-pearl-100 focus:outline-none focus:ring-2 focus:ring-sun-500"
          >
            <option value="contract">Contract</option>
            <option value="invoice">Invoice</option>
            <option value="quality_report">Quality Report</option>
          </select>
        </div>

        {/* Analysis Type */}
        <div>
          <label className="block text-sm font-medium text-pearl-300 mb-2">
            Analysis Type
          </label>
          <select
            value={analysisType}
            onChange={(e) => setAnalysisType(e.target.value as any)}
            className="w-full px-3 py-2 bg-pearl-800/50 border border-pearl-700/30 rounded-lg text-pearl-100 focus:outline-none focus:ring-2 focus:ring-sun-500"
          >
            <option value="summary">Summary</option>
            <option value="risks">Risk Identification</option>
            <option value="compliance">Compliance Check</option>
            <option value="trends">Trend Analysis</option>
          </select>
        </div>

        {/* Document Text */}
        <div>
          <label className="block text-sm font-medium text-pearl-300 mb-2">
            Document Text
          </label>
          <textarea
            value={documentText}
            onChange={(e) => setDocumentText(e.target.value)}
            placeholder="Paste or type document text here..."
            className="w-full h-40 px-3 py-2 bg-pearl-800/50 border border-pearl-700/30 rounded-lg text-pearl-100 placeholder-pearl-500 focus:outline-none focus:ring-2 focus:ring-sun-500 resize-none"
          />
        </div>

        {/* Analyze Button */}
        <button
          onClick={analyzeDocument}
          disabled={loading || !documentText.trim()}
          className="w-full px-4 py-2 bg-gradient-to-r from-saturn-500 to-sun-500 text-white rounded-lg hover:from-saturn-600 hover:to-sun-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center space-x-2"
        >
          {loading ? (
            <>
              <ArrowPathIcon className="w-4 h-4 animate-spin" />
              <span>Analyzing...</span>
            </>
          ) : (
            <>
              <SparklesIcon className="w-4 h-4" />
              <span>Analyze Document</span>
            </>
          )}
        </button>

        {/* Error */}
        {error && (
          <div className="p-3 bg-mars-500/20 border border-mars-500/30 rounded-lg">
            <p className="text-mars-200 text-sm">{error}</p>
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-4">
            {/* Metadata */}
            <div className="p-3 bg-pearl-800/30 rounded-lg border border-pearl-700/30">
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div>
                  <span className="text-pearl-500">Type:</span>
                  <span className="text-pearl-200 ml-2 capitalize">{result.metadata.document_type}</span>
                </div>
                <div>
                  <span className="text-pearl-500">Analysis:</span>
                  <span className="text-pearl-200 ml-2 capitalize">{result.metadata.analysis_type}</span>
                </div>
                <div>
                  <span className="text-pearl-500">Words:</span>
                  <span className="text-pearl-200 ml-2">{result.metadata.word_count}</span>
                </div>
              </div>
            </div>

            {/* Key Insights */}
            {result.insights.length > 0 && (
              <div className="p-3 bg-sun-500/10 border border-sun-500/30 rounded-lg">
                <h4 className="text-sm font-semibold text-sun-400 mb-2">Key Insights</h4>
                <ul className="space-y-1">
                  {result.insights.map((insight, i) => (
                    <li key={i} className="text-sm text-pearl-200 flex items-start">
                      <span className="text-sun-400 mr-2">•</span>
                      <span>{insight}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Full Analysis */}
            <div className="p-3 bg-pearl-800/30 rounded-lg border border-pearl-700/30">
              <h4 className="text-sm font-semibold text-pearl-200 mb-2">Analysis Result</h4>
              <div className="text-sm text-pearl-300 whitespace-pre-wrap">{result.analysis}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
