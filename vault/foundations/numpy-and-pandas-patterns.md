# NumPy and Pandas Patterns

Vectorise or suffer. A Python loop over a DataFrame is usually far slower than
the vectorised form and harder to read.

Patterns worth memorising:
- Boolean masking instead of filtering in a loop
- groupby and agg instead of manual accumulation
- Broadcasting - a shape (3,1) and a shape (1,4) array combine into (3,4).
  Half my shape errors come from not picturing this.
- loc for labels, iloc for positions, never chained assignment

Shape mismatches are the most common bug I hit. Printing the shape before every
matrix operation is not a beginner crutch, it is the fix.

Related: [[Python for Data Work]], [[Linear Algebra for ML]]
