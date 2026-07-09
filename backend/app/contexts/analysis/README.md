# Analysis Context

Owns ranking, trend, signal, strategy and analysis queries.

This context is query-side first. It may use optimized SQL, read models, Pandas, Numpy and cache adapters in `infrastructure` without forcing every query through domain aggregates.
