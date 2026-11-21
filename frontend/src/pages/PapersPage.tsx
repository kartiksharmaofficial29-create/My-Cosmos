import { Fragment, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { AsyncView } from "../components/AsyncView";
import { Chip, CosmicLoader, EmptyState } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import type { PaperSort } from "../types";

const PAGE_SIZE = 25;

export function PapersPage() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const topic = params.get("topic") ?? "";
  const country = params.get("country") ?? "";
  const sort = (params.get("sort") as PaperSort) || "newest";
  const page = Number(params.get("page") ?? 1);

  const facets = useAsync(() => api.getFacets(), []);
  const result = useAsync(
    () => api.queryPapers({ q, topic: topic || undefined, country: country || undefined, sort, page, page_size: PAGE_SIZE }),
    [q, topic, country, sort, page],
  );
  const [open, setOpen] = useState<Set<string>>(new Set());
  const [text, setText] = useState(q);

  /** Change one filter; any filter change returns to page 1. */
  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    if (key !== "page") next.delete("page");
    setParams(next);
  };
  const toggle = (id: string) => setOpen((s) => {
    const n = new Set(s);
    if (n.has(id)) n.delete(id); else n.add(id);
    return n;
  });

  return (
    <div className="container-cosmos py-10">
      <p className="eyebrow">Research explorer</p>
      <h1 className="mt-1 text-3xl font-semibold">Papers</h1>
      <p className="mt-2 text-navy-500">Filter, sort and inspect the corpus. The address keeps your filters, so you can share the view.</p>

      {/* Filters */}
      <div className="mt-6 flex flex-wrap items-end gap-3 text-sm">
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); update("q", text.trim()); }}>
          <label htmlFor="kw" className="sr-only">Keyword</label>
          <input id="kw" value={text} onChange={(e) => setText(e.target.value)} placeholder="Keyword…"
            className="glass h-10 rounded-full px-4 focus:outline-none" />
          <button type="submit" className="h-10 rounded-full bg-violet-500 px-4 font-medium text-white hover:bg-violet-600">Filter</button>
        </form>
        <AsyncView state={facets} loading="Loading filters…">
          {(f) => (
            <>
              <label className="flex flex-col gap-1">Topic
                <select value={topic} onChange={(e) => update("topic", e.target.value)} className="h-10 rounded-lg border border-lavender-100 bg-white/70 px-2">
                  <option value="">All topics</option>
                  {f.topics.map((t) => <option key={t.value} value={t.value}>{t.value} ({t.count})</option>)}
                </select>
              </label>
              <label className="flex flex-col gap-1">Country
                <select value={country} onChange={(e) => update("country", e.target.value)} className="h-10 rounded-lg border border-lavender-100 bg-white/70 px-2">
                  <option value="">All countries</option>
                  {f.countries.map((c) => <option key={c.value} value={c.value}>{c.value} ({c.count})</option>)}
                </select>
              </label>
            </>
          )}
        </AsyncView>
        <label className="flex flex-col gap-1">Sort
          <select value={sort} onChange={(e) => update("sort", e.target.value)} className="h-10 rounded-lg border border-lavender-100 bg-white/70 px-2">
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
            <option value="title">Title A–Z</option>
          </select>
        </label>
        {(q || topic || country) && (
          <button type="button" onClick={() => { setText(""); setParams({}); }} className="h-10 text-violet-600 hover:underline">Clear all</button>
        )}
      </div>

      {/* Results */}
      <div className="mt-6">
        {result.status === "loading" && <CosmicLoader label="Filtering the research universe…" />}
        {result.status === "error" && <EmptyState title="Couldn't load papers." hint={result.error.message} />}
        {result.status === "ready" && (result.data.total === 0
          ? <EmptyState title="No papers match these filters." hint="Try removing a filter." />
          : (
            <>
              <p className="mb-2 text-sm tabular-nums text-navy-500" aria-live="polite">
                {result.data.total.toLocaleString()} papers · page {page} of {Math.ceil(result.data.total / PAGE_SIZE)}
              </p>
              <div className="glass overflow-x-auto">
                <table className="w-full min-w-[720px] text-left text-sm">
                  <caption className="sr-only">Research papers</caption>
                  <thead className="border-b border-lavender-100 text-xs uppercase tracking-wider text-navy-500">
                    <tr>
                      <th scope="col" className="w-10 px-3 py-3"><span className="sr-only">Details</span></th>
                      <th scope="col" className="px-3 py-3">Paper</th>
                      <th scope="col" className="px-3 py-3">Year</th>
                      <th scope="col" className="px-3 py-3">Country</th>
                      <th scope="col" className="px-3 py-3">Topic</th>
                      <th scope="col" className="px-3 py-3">Method</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.data.items.map((p) => {
                      const isOpen = open.has(p.paper_id);
                      return (
                        <Fragment key={p.paper_id}>
                          <tr className="border-b border-lavender-50 align-top hover:bg-lavender-50/60">
                            <td className="px-3 py-3">
                              <button type="button" onClick={() => toggle(p.paper_id)} aria-expanded={isOpen}
                                className="grid h-6 w-6 place-items-center rounded-full hover:bg-lavender-100">
                                <span className="sr-only">{isOpen ? "Hide" : "Show"} abstract</span>
                                <span aria-hidden className={`transition-transform ${isOpen ? "rotate-90" : ""}`}>›</span>
                              </button>
                            </td>
                            <td className="px-3 py-3"><Link to={`/papers/${p.paper_id}`} className="font-medium hover:text-violet-600">{p.title}</Link></td>
                            <td className="px-3 py-3 tabular-nums">{p.publication_year}</td>
                            <td className="px-3 py-3">{p.country ?? "—"}</td>
                            <td className="px-3 py-3">
                              <div className="flex flex-wrap gap-1">
                                {p.derived.topics.map((t) => <Chip key={t} to={`/papers?topic=${encodeURIComponent(t)}`}>{t}</Chip>)}
                              </div>
                            </td>
                            <td className="px-3 py-3">{p.derived.methods.join(", ")}</td>
                          </tr>
                          {isOpen && (
                            <tr className="bg-lavender-50/40">
                              <td />
                              <td colSpan={5} className="px-3 pb-4 text-navy-700">{p.abstract}</td>
                            </tr>
                          )}
                        </Fragment>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <nav aria-label="Pagination" className="mt-4 flex items-center gap-3 text-sm">
                <button type="button" disabled={page <= 1} onClick={() => update("page", String(page - 1))}
                  className="rounded-full bg-white/70 px-4 py-1.5 disabled:opacity-40">‹ Previous</button>
                <button type="button" disabled={page * PAGE_SIZE >= result.data.total} onClick={() => update("page", String(page + 1))}
                  className="rounded-full bg-white/70 px-4 py-1.5 disabled:opacity-40">Next ›</button>
              </nav>
            </>
          ))}
      </div>
    </div>
  );
}