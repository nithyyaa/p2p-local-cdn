
import { useState } from "react";

const demoMetrics = {
  bandwidthSaved: 78,
  cacheHitRate: 85,
  peerTraffic: 68,
  fasterDelivery: 3.4,
};

export default function Advantages() {
  const [activeTab, setActiveTab] = useState("overview");

  const advantages = [
    {
      icon: "📉",
      title: "Reduced Origin Bandwidth",
      description:
        "Repeated downloads can be served by peers and cached copies instead of repeatedly fetching data from the origin.",
      benefit: "Lower origin traffic",
      color: "green",
    },
    {
      icon: "⚡",
      title: "Faster Content Delivery",
      description:
        "Retrieve available chunks from nearby peers or local cache to reduce unnecessary origin requests.",
      benefit: "Potentially faster downloads",
      color: "blue",
    },
    {
      icon: "🌐",
      title: "Peer-to-Peer Distribution",
      description:
        "Connected computers can share file chunks, distributing delivery workload across participating nodes.",
      benefit: "Distributed delivery",
      color: "purple",
    },
    {
      icon: "💾",
      title: "Intelligent Caching",
      description:
        "Verified chunks can be reused for subsequent requests, reducing duplicate transfers.",
      benefit: "Reuse downloaded content",
      color: "orange",
    },
    {
      icon: "🔐",
      title: "Chunk Verification",
      description:
        "Verify downloaded chunks against expected hashes to help detect corrupted or altered content.",
      benefit: "Content integrity",
      color: "cyan",
    },
    {
      icon: "📊",
      title: "Transfer Visibility",
      description:
        "Monitor peer activity, cache usage, origin traffic, and transfer performance through one dashboard.",
      benefit: "Measurable performance",
      color: "pink",
    },
  ];

  const comparison = [
    {
      feature: "Content delivery",
      traditional: "Primarily from origin",
      peerlight: "Origin, peers, and cache",
    },
    {
      feature: "Repeated requests",
      traditional: "May download repeatedly",
      peerlight: "Can reuse cached chunks",
    },
    {
      feature: "Bandwidth usage",
      traditional: "Higher origin traffic potential",
      peerlight: "Can reduce origin traffic",
    },
    {
      feature: "Distribution workload",
      traditional: "Concentrated at origin",
      peerlight: "Can be distributed among peers",
    },
    {
      feature: "Integrity checks",
      traditional: "Depends on implementation",
      peerlight: "Chunk hash verification",
    },
    {
      feature: "Network visibility",
      traditional: "Depends on monitoring tools",
      peerlight: "Peer and transfer monitoring",
    },
  ];

  const cards = [
    {
      label: "Potential Origin Bandwidth Savings",
      value: `${demoMetrics.bandwidthSaved}%`,
      icon: "📉",
      description: "Illustrative demo value",
    },
    {
      label: "Illustrative Cache Hit Rate",
      value: `${demoMetrics.cacheHitRate}%`,
      icon: "💾",
      description: "Example cache performance",
    },
    {
      label: "Illustrative Peer Traffic Share",
      value: `${demoMetrics.peerTraffic}%`,
      icon: "🌐",
      description: "Example distributed traffic",
    },
    {
      label: "Potential Delivery Improvement",
      value: `${demoMetrics.fasterDelivery}×`,
      icon: "⚡",
      description: "Illustrative comparison",
    },
  ];

  return (
    <div className="min-h-screen bg-[#0b0f14] p-6 text-slate-100 md:p-9">
      <div className="mx-auto max-w-7xl space-y-8">
        {/* Header */}
        <header className="flex flex-col justify-between gap-5 md:flex-row md:items-center">
          <div>
            <div className="mb-3 flex items-center gap-2 text-sm text-cyan-400">
              <span className="h-2 w-2 rounded-full bg-cyan-400" />
              PEERLIGHT / PERFORMANCE INSIGHTS
            </div>

            <h1 className="text-3xl font-bold tracking-tight md:text-4xl">
              Advantages & Impact
            </h1>

            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
              Discover how peer-to-peer distribution and content caching can
              reduce origin traffic and improve content delivery efficiency.
            </p>
          </div>

          <div className="flex items-center gap-3 self-start rounded-xl border border-slate-700 bg-slate-900 px-4 py-3">
            <span className="text-2xl">🚀</span>
            <div>
              <p className="text-sm font-semibold">Peerlight P2P CDN</p>
              <p className="text-xs text-slate-400">
                Distributed content delivery
              </p>
            </div>
          </div>
        </header>

        {/* Demo notice */}
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 px-5 py-4">
          <p className="text-sm font-semibold text-amber-300">
            Demo metrics — illustrative data
          </p>
          <p className="mt-1 text-sm leading-6 text-slate-400">
            The performance figures below are examples for presentation
            purposes, not live measurements. Actual savings depend on cache
            hits, peer availability, file sizes, and network conditions.
          </p>
        </div>

        {/* Navigation */}
        <div className="flex flex-wrap gap-2 border-b border-slate-800 pb-4">
          {[
            ["overview", "Overview"],
            ["comparison", "Traditional CDN vs Peerlight"],
            ["workflow", "How It Works"],
          ].map(([id, label]) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`rounded-lg px-4 py-2.5 text-sm font-medium transition ${
                activeTab === id
                  ? "bg-cyan-500 text-slate-950"
                  : "border border-slate-700 bg-slate-900 text-slate-300 hover:border-cyan-500/60"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {activeTab === "overview" && (
          <>
            {/* KPI cards */}
            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {cards.map((card) => (
                <div
                  key={card.label}
                  className="rounded-2xl border border-slate-800 bg-[#121820] p-5 transition hover:-translate-y-1 hover:border-cyan-500/50"
                >
                  <div className="flex items-start justify-between">
                    <p className="max-w-[190px] text-sm leading-5 text-slate-400">
                      {card.label}
                    </p>
                    <span className="text-2xl">{card.icon}</span>
                  </div>

                  <p className="mt-5 text-3xl font-bold text-cyan-300">
                    {card.value}
                  </p>

                  <p className="mt-2 text-xs text-amber-400">
                    {card.description}
                  </p>
                </div>
              ))}
            </section>

            {/* Bandwidth comparison */}
            <section className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-2xl border border-slate-800 bg-[#121820] p-6">
                <h2 className="text-lg font-semibold">
                  Origin Bandwidth Impact
                </h2>

                <p className="mt-2 text-sm text-slate-400">
                  Illustrative distribution of 100 units of requested data.
                </p>

                <div className="mt-7 space-y-6">
                  {[
                    {
                      label: "Traditional origin delivery",
                      value: 100,
                      color: "bg-slate-500",
                    },
                    {
                      label: "Peerlight origin delivery",
                      value: 22,
                      color: "bg-cyan-400",
                    },
                  ].map((item) => (
                    <div key={item.label}>
                      <div className="mb-2 flex justify-between gap-3 text-sm">
                        <span className="text-slate-300">{item.label}</span>
                        <span className="font-semibold">{item.value}%</span>
                      </div>

                      <div className="h-3 overflow-hidden rounded-full bg-slate-800">
                        <div
                          className={`h-full rounded-full ${item.color}`}
                          style={{ width: `${item.value}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-7 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
                  <p className="text-sm font-semibold text-emerald-300">
                    Potential benefit: less origin traffic
                  </p>
                  <p className="mt-1 text-sm leading-6 text-slate-400">
                    When peers and cache serve more requests, the origin may
                    need to deliver less data.
                  </p>
                </div>
              </div>

              {/* Delivery sources */}
              <div className="rounded-2xl border border-slate-800 bg-[#121820] p-6">
                <h2 className="text-lg font-semibold">
                  Distributed Delivery Model
                </h2>

                <p className="mt-2 text-sm text-slate-400">
                  Content can be delivered through three sources.
                </p>

                <div className="mt-6 space-y-4">
                  {[
                    {
                      label: "Local cache",
                      percent: 40,
                      icon: "💾",
                      color: "bg-emerald-400",
                    },
                    {
                      label: "Connected peers",
                      percent: 35,
                      icon: "🌐",
                      color: "bg-cyan-400",
                    },
                    {
                      label: "Original source",
                      percent: 25,
                      icon: "🗄️",
                      color: "bg-violet-400",
                    },
                  ].map((source) => (
                    <div
                      key={source.label}
                      className="rounded-xl border border-slate-800 bg-slate-900/60 p-4"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span className="text-xl">{source.icon}</span>
                          <span className="text-sm font-medium">
                            {source.label}
                          </span>
                        </div>
                        <span className="text-sm font-bold text-slate-300">
                          {source.percent}%
                        </span>
                      </div>

                      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-800">
                        <div
                          className={`h-full rounded-full ${source.color}`}
                          style={{ width: `${source.percent}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                <p className="mt-5 text-xs leading-5 text-amber-400">
                  Example proportions only; actual delivery sources depend on
                  measured transfer results.
                </p>
              </div>
            </section>

            {/* Advantages */}
            <section>
              <div className="mb-5">
                <h2 className="text-xl font-bold">Why Peerlight?</h2>
                <p className="mt-2 text-sm text-slate-400">
                  The core benefits of peer-assisted content distribution.
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {advantages.map((item) => (
                  <article
                    key={item.title}
                    className="rounded-2xl border border-slate-800 bg-[#121820] p-5 transition hover:border-slate-600"
                  >
                    <span className="text-3xl">{item.icon}</span>

                    <h3 className="mt-4 font-semibold">{item.title}</h3>

                    <p className="mt-2 text-sm leading-6 text-slate-400">
                      {item.description}
                    </p>

                    <div className="mt-5 inline-flex rounded-full border border-cyan-500/20 bg-cyan-500/10 px-3 py-1.5 text-xs font-medium text-cyan-300">
                      {item.benefit}
                    </div>
                  </article>
                ))}
              </div>
            </section>
          </>
        )}

        {activeTab === "comparison" && (
          <section className="overflow-hidden rounded-2xl border border-slate-800 bg-[#121820]">
            <div className="border-b border-slate-800 p-6">
              <h2 className="text-xl font-bold">
                Traditional Delivery vs Peerlight
              </h2>
              <p className="mt-2 text-sm text-slate-400">
                Compare the delivery approaches and potential benefits.
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[620px] text-left text-sm">
                <thead className="bg-slate-900/80 text-slate-400">
                  <tr>
                    <th className="px-6 py-4 font-medium">Feature</th>
                    <th className="px-6 py-4 font-medium">
                      Traditional delivery
                    </th>
                    <th className="px-6 py-4 font-medium text-cyan-300">
                      Peerlight
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {comparison.map((row) => (
                    <tr
                      key={row.feature}
                      className="border-t border-slate-800"
                    >
                      <td className="px-6 py-5 font-medium">{row.feature}</td>
                      <td className="px-6 py-5 text-slate-400">
                        {row.traditional}
                      </td>
                      <td className="px-6 py-5 text-emerald-300">
                        {row.peerlight}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {activeTab === "workflow" && (
          <section className="rounded-2xl border border-slate-800 bg-[#121820] p-6 md:p-8">
            <h2 className="text-xl font-bold">
              How Peerlight Delivers Content
            </h2>

            <p className="mt-2 text-sm leading-6 text-slate-400">
              A peer-assisted content delivery workflow with chunk
              verification.
            </p>

            <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {[
                {
                  step: "01",
                  icon: "📥",
                  title: "Request",
                  text: "A node requests a file and obtains its chunk manifest.",
                },
                {
                  step: "02",
                  icon: "🔎",
                  title: "Discover",
                  text: "The system checks available local cache entries and peers.",
                },
                {
                  step: "03",
                  icon: "🔄",
                  title: "Retrieve",
                  text: "Available chunks are fetched from peers, cache, or origin.",
                },
                {
                  step: "04",
                  icon: "🛡️",
                  title: "Verify",
                  text: "Chunks are checked against expected hashes before use.",
                },
              ].map((step) => (
                <div
                  key={step.step}
                  className="rounded-xl border border-slate-700 bg-slate-900 p-5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold tracking-widest text-cyan-400">
                      STEP {step.step}
                    </span>
                    <span className="text-2xl">{step.icon}</span>
                  </div>

                  <h3 className="mt-5 font-semibold">{step.title}</h3>

                  <p className="mt-2 text-sm leading-6 text-slate-400">
                    {step.text}
                  </p>
                </div>
              ))}
            </div>

            <div className="mt-8 rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-5">
              <h3 className="font-semibold text-cyan-300">
                The key advantage
              </h3>
              <p className="mt-2 text-sm leading-6 text-slate-300">
                As more nodes obtain and share verified content, Peerlight can
                reuse cached data and distribute delivery work instead of
                relying entirely on the original source.
              </p>
            </div>
          </section>
        )}

        {/* Footer */}
        <footer className="border-t border-slate-800 pt-5 text-center text-xs leading-6 text-slate-500">
          Peerlight P2P LAN CDN · Advantages & Impact
          <br />
          Illustrative figures are not live measurements or guaranteed
          performance improvements.
        </footer>
      </div>
    </div>
  );
}
