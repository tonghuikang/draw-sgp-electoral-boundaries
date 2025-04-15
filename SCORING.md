I elaborate on the rationale behind the scoring algorithm here.

There are five numbers that I calculate for each constituency.
Each number is between zero and one.

For each constituency, we can measure how good they are:
- Electoral balance - We want the electors per member to be close to the mean
- Non-enclavity - We do not want constituencies that are an enclave of another constituency
- Compactness - We want the constituency to be roundish
- Convexity - We want the constituency to have a convex shape
- Relevance - We want the assigned name of the constituency to reflect its location

# Electoral Balance

The electoral balance is calculated by:
- Calculate the mean electors per member by dividing the total number of electors by the total number of members
- Calculate the electors per member of the constituency
- Calculate the geometric ratio between the electors per member of the constituency and the overall electors per member
- The electoral balance is this geometric ratio

The geometric ratio between two positive numbers `a` and `b` is `min(a/b, b/a)`.
This ratio is between zero and one, with 1 representing perfect balance.

It is possible that an assignment could sacrifice electoral balance for some constituencies to achieve a near perfect score for other constituencies.
This is why the final constituency score is bounded by the electoral balance score, to prevent such manipulations.

# Nonenclavity

We do not want constituencies that are an enclave of another constituency.

Nonenclavity is calculated by:
- Districts with adjacency to external districts are considered boundary districts
- Count how many of these boundary districts are adjacent to each external constituency
- Calculate the enclavity as the maximum adjacent constituency count divided by the number of boundary districts
- If the enclavity is less than 0.5, award the full score of 1 for non-enclavity
- If the enclavity is 1, award a score of 0 for non-enclavity
- If the enclavity is greater than 0.5, apply a formula to interpolate the non-enclavity score: `1 - (enclavity - 0.5) / 0.5`

The purpose of this metric is to prevent a constituency from being largely surrounded by another single constituency. It's acceptable for a constituency to border multiple other constituencies, but being predominantly bordered by just one constituency is penalized.

Special handling is implemented to avoid penalizing coastal constituencies. For example, Pasir Ris-Changi should have full marks for non-enclavity despite being at the edge of the map.

# Compactness

Compactness measures how "round" a constituency is.

Compactness is calculated by:
- Compute chord lengths through the centroid of the constituency at 720 different angles from 0 to π
- For each angle, draw a line through the centroid and measure the length of the intersection with the constituency
- Calculate the geometric ratio between each chord length and the median chord length
- Take the average of these geometric ratios

This approach gives a measure of how circular and balanced the shape is, with higher scores (closer to 1) indicating more compact shapes. Unlike the traditional isoperimetric quotient, this method is less sensitive to small boundary irregularities and better captures the visual compactness of a shape.

# Convexity

Convexity measures how much a shape resembles its convex hull - essentially how "dented" or "concave" it is.

Convexity is calculated by:
- Compute the area of the constituency
- Compute the area of the convex hull of this geometry (the smallest convex polygon containing the constituency)
- Take the ratio of the constituency area to the convex hull area

This ratio is between 0 and 1, with 1 being perfectly convex (no indentations). Lower scores indicate constituencies with more irregular shapes that have concave sections.

Why calculate both compactness and convexity?
- A constituency could be completely convex but not compact (e.g., a long rectangle)
- A constituency could be reasonably compact but have concave sections
- Both measures together ensure the constituency boundaries are reasonable and not gerrymandered

Updates will be made to not penalize the assignment if non-convex polling districts are at the boundary.

# Relevance

We want the name of the constituency to reflect the place where constituents live.

Relevance is calculated by:
- Examine the MRT station names within each polling district of the constituency
- Compare these names with the constituency name (including checking name aliases from a predefined list)
- For single-name constituencies, calculate what proportion of electors live in districts with matching MRT names
- For double-barrel names (e.g., "Jurong East-Bukit Batok"), handling partial matches differently:
  - Full match: When all constituency name parts match MRT stations in a district
  - Partial match: When only some constituency name parts match

The calculation is weighted by elector population, giving more influence to districts with more electors. The algorithm also handles name aliases (defined in raw_data/name_aliases.json) to account for variations in place names.

A high relevance score means constituents can readily identify with the name of their constituency based on familiar local landmarks or area names.

# The Constituency Score

The constituency score is calculated by:
- Take the average of all five metrics (electoral balance, non-enclavity, compactness, convexity, and relevance)
- Apply an upper bound equal to the electoral balance score

Why bound by electoral balance?
This prevents assignments from sacrificing electoral balance in some constituencies to achieve high scores in other metrics.
Electoral balance is a fundamental principle of fair representation, so no constituency's overall score should exceed its electoral balance score.

# The Overall Score

The overall score is the score for the entire constituency assignment.

The overall score is calculated by:
- Take the member-weighted average of all constituency scores
- This gives more weight to GRCs with more members than SMCs

This final score provides a single metric to evaluate the quality of the entire electoral boundary map. With the current boundary assignment, the overall score is approximately 77.35%.