import { api } from "../api";
import { AsyncView } from "../components/AsyncView";
import { StatCard } from "../components/ui";
import { useAsync } from "../hooks/useAsync";

export function ExplorePage() {
  const stats = useAsync(() => api.getStats(), []);

  return (
    <section className="container-cosmos py-20">
      <p className="eyebrow">Space Research Intelligence</p>
      <h1 className="mt-3 text-4xl font-bold sm:text-6xl">
        Explore humanity's knowledge <span className="text-violet-500">beyond Earth.</span>
      </h1>

      <div className="mt-10">
        <AsyncView state={stats} loading="Counting the stars…">
          {(s) => (
            <>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <StatCard value={s.papers} label="Research papers" />
                <StatCard value={s.countries} label="Countries" />
                <StatCard value={s.topics} label="Research topics" />
                <StatCard value={s.organizations} label="Organizations" />
              </div>
              {s.synthetic && (
                <p className="mt-3 text-sm text-navy-500">Demo data: these are synthetic records, not real research.</p>
              )}
            </>
          )}
        </AsyncView>
      </div>
    </section>
  );
}
