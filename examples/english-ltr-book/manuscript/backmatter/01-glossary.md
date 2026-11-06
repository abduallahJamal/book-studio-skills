# Glossary

- **Backpressure:** Signaling upstream senders to slow down or shed load when downstream consumers reach capacity.
- **Bulkhead:** Partitioned thread, memory, or connection pools isolating one dependency's failure from unrelated paths.
- **Idempotency Key:** Client-generated unique token guaranteeing that repeated attempts execute a side effect at most once.
- **Retry Budget:** Ratio limit (`10%`) bounding total retry traffic across an entire process.
