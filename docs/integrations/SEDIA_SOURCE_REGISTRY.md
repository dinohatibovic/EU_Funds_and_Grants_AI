# SEDIA and Grant Source Registry

## Scope

This phase introduces an isolated source registry and
transport-only SEDIA client.

It does not:

- modify the public search API
- write SEDIA records to PostgreSQL
- write SEDIA records to ChromaDB
- change the existing grant dataset
- expose unverified records as active grants
- schedule a production synchronization

## Authority levels

1. Official publisher or official API
2. Official programme or distribution portal
3. Verified aggregator
4. Unverified informational source

## Grounding rule

The language model is not a grant data source.

Dynamic claims including status, deadline, budget,
eligibility, co-financing, official URL, and required
documentation must come from validated canonical records.

Missing values remain missing and must not be inferred.

## Current phase

The current phase introduces:

- validated source configuration
- immutable SEDIA settings
- asynchronous HTTP transport
- domain exceptions
- mocked transport tests
- a synthetic response fixture

## Later phases

1. Canonical GrantRecordV3
2. SEDIA pagination and checkpoints
3. Change detection and hashing
4. PostgreSQL version history
5. Incremental ChromaDB synchronization
6. Grounded AI response contract
7. Scheduled synchronization
8. National source adapters
