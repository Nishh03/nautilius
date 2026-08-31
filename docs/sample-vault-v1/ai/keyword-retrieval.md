# Keyword Retrieval

Scoring documents by how many query terms they contain, weighted by where the
term appears. Title matches count more than body matches.

Cheap, explainable, and needs no model. The weakness is vocabulary mismatch:
a note about "cars" will not match a question about "automobiles".

Upgrade path is [[vector-embeddings]], which fixes exactly that.

See also [[retrieval-augmented-generation]]
