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

This is the procedure to calculate the electoral balance:
- Calculate the global electors per member by dividing the total number of electors by the total number of members
- Calculate the local electors per member for each constituency
- Calculate the geometric ratio between local electors per member and the global electors per member, for each constituency.
- The electoral balance is this geometric ratio

The geometric ratio between two positive numbers `a` and `b` is `min(a/b, b/a)`.
The value of the geometric ratio is between zero and one, with 1 representing perfect balance.


# Nonenclavity

We do not want constituencies that are an enclave of another constituency.

This is the procedure to calculate nonenclavity:
- Districts with adjacency to external districts are considered boundary districts
- Count how many of these boundary districts are adjacent to each external constituency
- Calculate the enclavity as the maximum adjacent constituency count divided by the number of boundary districts
- If the enclavity is less than 0.5, award the full score of 1 for non-enclavity
- If the enclavity is 1, award a score of 0 for non-enclavity
- If the enclavity is greater than 0.5, apply a formula to interpolate the non-enclavity score: `1 - (enclavity - 0.5) / 0.5`

The purpose of this metric is to prevent a constituency from being largely surrounded by another single constituency. It's acceptable for a constituency to border multiple other constituencies, but being predominantly bordered by just one constituency is penalized.

I intend to redesign how this metric is calculated. For example, Pasir Ris-Changi should have full marks for non-enclavity despite being at the edge of the map.


# Compactness

Compactness measures how "round" a constituency is.

This is the procedure to calculate compactness:
- Draw a line through the centroid of the constituency at 720 different angles from 0 to π
- Compute the intersection length between the line and the constituency
- Calculate the median intersection length
- Calculate the geometric ratio between the median intersection length and each intersection length
- Take the average of these geometric ratios

This approach gives a measure of how circular and balanced the shape is, with higher scores (closer to 1) indicating more compact shapes.


# Convexity

Convexity measures how much a shape resembles its convex hull - essentially how "dented" or "concave" it is.

This is the procedure to calculate convexity:
- Compute the area of the constituency
- Compute the area of the convex hull of this geometry (the smallest convex polygon containing the constituency)
- Take the ratio of the constituency area to the convex hull area

This ratio is between 0 and 1, with 1 being perfectly convex (no indentations). Lower scores indicate constituencies with more irregular shapes that have concave sections.

Why calculate both compactness and convexity?
- A constituency could be completely convex but not compact (e.g., a long rectangle)
- A constituency could be reasonably compact but have concave sections
- Both measures together ensure the constituency boundaries are reasonable and not gerrymandered

I intend to make a small design change to the calculation of this metric to not penalize the assignment just for having non-convex polling districts at the boundary.


# Relevance

We want the name of the constituency to reflect the place where constituents live.

This is the procedure to calculate relevance:
- Consider the nearest MRTs for each polling district
- For single-name constituencies, calculate what proportion of electors live in districts with matching MRT names
- For double-barrel names (e.g., "Jurong East-Bukit Batok")
   - Count the proportion of electors who live in districts that matches both MRT names `a`
   - Count the proportion of electors who live in districts that matches only one of the MRT names `b1`, `b2`
   - Take a weighted sum - a + b1 / √n + b2 / √n
- Aliases were considered to be equivalent (Nee Soon and Yishun, Chua Chu Kang and Choa Chu Kang)

A high relevance score means constituents can readily identify with the name of their constituency based on familiar local landmarks or area names.

I intend to expand the list of names that are considered to be relevant - with road names for example.


# The Constituency Score

The overall score is the score for the constituency.

This is the procedure to calculate the constituency score:
- Take the average of all five metrics (electoral balance, non-enclavity, compactness, convexity, and relevance)
- Apply an upper bound equal to the electoral balance score

Having individual scores for each constituency allows us to understand which constituency could use the most improvement.


# The Overall Score

The overall score is the score for the entire constituency assignment.

This is the procedure to calculate the overall score:
- Take the member-weighted average of all constituency scores
- This gives more weight to GRCs with more members than SMCs
- Apply an upper bound equal to the minimum electoral balance score

I bound the constituency score and the overall score with the electoral balance score to prevent assignments from greatly sacrificing electoral balance in some constituencies to achieve high scores in other metrics. Electoral balance is a fundamental principle of fair representation. If the overall score is above 90%, we are guaranteed that the representation power of each constituency does not deviate by more than 10%.

This final score provides a single metric to evaluate the quality of the entire electoral boundary map. With the current boundary assignment, the overall score is approximately 77.35%.