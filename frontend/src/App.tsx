import { useState } from "react";
import type { FormEvent } from "react";
import "./index.css";

const API_BASE_URL = "http://localhost:8000";

function App() {
 const [query, setQuery] = useState("");
 interface SearchResult {
  url: string;
  tfidf_score: number;
  pagerank: number;
  total_score: number;
 }

 const [results, setResults] = useState<SearchResult[]>([]);
 const [top, setTop] = useState<number>(5);
 const [loading, setLoading] = useState(false);
 const [error, setError] = useState<string | null>(null);
 const [elapsedMs, setElapsedMs] = useState<number | null>(null);

 const handleSearch = async (e: FormEvent) => {
  e.preventDefault();
  const trimmed = query.trim();
  if (!trimmed) {
   setError("Please enter a query.");
   setResults([]);
   setElapsedMs(null);
   return;
  }

  if (top <= 0) {
   setError("Number of results must be at least 1.");
   setResults([]);
   setElapsedMs(null);
   return;
  }

  setLoading(true);
  setError(null);
  setElapsedMs(null);

  try {
   const params = new URLSearchParams({
    q: trimmed,
    top: String(top),
   });

   const response = await fetch(`${API_BASE_URL}/search?${params.toString()}`);

   if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
   }

   const data: {
    query: string;
    results: SearchResult[];
    elapsed_ms: number;
    timed_out: boolean;
    message: string;
   } = await response.json();

   setResults(data.results || []);
   setElapsedMs(data.elapsed_ms ?? null);
  } catch (err: unknown) {
   const message =
    err instanceof Error
     ? err.message
     : "Something went wrong while searching.";
   setError(message);
   setResults([]);
   setElapsedMs(null);
  } finally {
   setLoading(false);
  }
 };

 return (
  <div className="app-root">
   <div className="app-card">
    <h1 className="app-title">Search Engine</h1>
    <p className="app-subtitle">
     Enter a query and we&apos;ll show matching URLs.
    </p>

    <form className="search-form" onSubmit={handleSearch}>
     <input
      type="text"
      value={query}
      onChange={(e) => setQuery(e.target.value)}
      placeholder="Search..."
      className="search-input"
     />
     <input
      type="number"
      min={1}
      max={50}
      value={top}
      onChange={(e) => setTop(Number(e.target.value) || 1)}
      className="search-input search-input-top"
      placeholder="Results"
     />
     <button type="submit" className="search-button" disabled={loading}>
      {loading ? "Searching…" : "Search"}
     </button>
    </form>

    {error && <div className="error-message">{error}</div>}

    {elapsedMs !== null && !error && (
     <p className="timing-info">Search time: {elapsedMs.toFixed(2)} ms</p>
    )}

    <div className="results-section">
     {results.length === 0 && !loading && !error && (
      <p className="results-empty">No results yet. Try a query.</p>
     )}

     {results.length > 0 && (
      <ul className="results-list">
       {results.map((result, index) => (
        <li key={result.url + index} className="results-item">
         <a href={result.url} target="_blank" rel="noreferrer">
          {result.url}
         </a>
         <span className="result-scores">
          Score: {result.total_score.toFixed(4)} (TF-IDF:{" "}
          {result.tfidf_score.toFixed(4)}, PageRank:{" "}
          {result.pagerank.toFixed(4)})
         </span>
        </li>
       ))}
      </ul>
     )}
    </div>
   </div>
  </div>
 );
}

export default App;
