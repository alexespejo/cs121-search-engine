import { type FormEvent, useState } from "react";

const API_BASE_URL = "http://0.0.0.0:8000";

function App() {
 const [query, setQuery] = useState("");
 const [results, setResults] = useState<string[]>([]);
 const [loading, setLoading] = useState(false);
 const [error, setError] = useState<string | null>(null);

 const handleSearch = async (e: FormEvent) => {
  e.preventDefault();
  const trimmed = query.trim();
  if (!trimmed) {
   setError("Please enter a query.");
   setResults([]);
   return;
  }

  setLoading(true);
  setError(null);

  try {
   const params = new URLSearchParams({
    q: trimmed,
    top: "5",
   });

   const response = await fetch(`${API_BASE_URL}/search?${params.toString()}`);

   if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
   }

   const data: string[] = await response.json();
   setResults(data);
  } catch (err: unknown) {
   const message =
    err instanceof Error
     ? err.message
     : "Something went wrong while searching.";
   setError(message);
   setResults([]);
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
     <button type="submit" className="search-button" disabled={loading}>
      {loading ? "Searching…" : "Search"}
     </button>
    </form>

    {error && <div className="error-message">{error}</div>}

    <div className="results-section">
     {results.length === 0 && !loading && !error && (
      <p className="results-empty">No results yet. Try a query.</p>
     )}

     {results.length > 0 && (
      <ul className="results-list">
       {results.map((url, index) => (
        <li key={url + index} className="results-item">
         <a href={url} target="_blank" rel="noreferrer">
          {url}
         </a>
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
