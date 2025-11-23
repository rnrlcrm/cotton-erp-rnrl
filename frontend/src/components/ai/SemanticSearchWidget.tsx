import React, { useState } from 'react';
import './SemanticSearchWidget.css';

interface SearchResult {
  id: string;
  document: string;
  metadata: Record<string, any>;
  distance: number;
}

interface SemanticSearchWidgetProps {
  collectionType?: 'contracts' | 'quality_reports' | 'invoices' | 'all';
  onResultClick?: (result: SearchResult) => void;
}

const SemanticSearchWidget: React.FC<SemanticSearchWidgetProps> = ({
  collectionType = 'all',
  onResultClick,
}) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  const search = async () => {
    if (!query.trim()) return;

    setLoading(true);

    try {
      const response = await fetch('/api/v1/ai/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          query,
          collection_type: collectionType,
          k: 10,
        }),
      });

      const data = await response.json();
      setResults(data.results || []);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      search();
    }
  };

  return (
    <div className="semantic-search-widget">
      <div className="search-header">
        <h3>🔍 Semantic Search</h3>
        <p>Search {collectionType} using natural language</p>
      </div>

      <div className="search-input-container">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Ask a question or describe what you're looking for..."
          disabled={loading}
        />
        <button onClick={search} disabled={loading || !query.trim()}>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>

      <div className="search-results">
        {results.length === 0 && !loading && query && (
          <div className="no-results">
            <p>No results found</p>
            <p className="hint">Try rephrasing your query</p>
          </div>
        )}

        {results.map((result) => (
          <div
            key={result.id}
            className="search-result-item"
            onClick={() => onResultClick?.(result)}
          >
            <div className="result-header">
              <span className="result-type">
                {result.metadata.document_type || 'Document'}
              </span>
              <span className="result-score">
                {Math.round((1 - result.distance) * 100)}% match
              </span>
            </div>
            <div className="result-content">
              {result.document.substring(0, 200)}...
            </div>
            <div className="result-metadata">
              {Object.entries(result.metadata)
                .slice(0, 3)
                .map(([key, value]) => (
                  <span key={key} className="metadata-tag">
                    {key}: {String(value)}
                  </span>
                ))}
            </div>
          </div>
        ))}

        {loading && (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Searching...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SemanticSearchWidget;
