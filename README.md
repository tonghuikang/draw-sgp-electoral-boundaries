# Evaluating and Assigning Singapore Constituencies

## How to evaluate constituency assignment

We assume that we are given the polling districts and we cannot change them.

The task of drawing the electoral boundaries is to assign constituency names and polling districts.

For each constituency, we can measure how good they are:
- Electoral balance - We want the electors per member to be close to the mean
- Nonenclavity - We do not want constituencies that are an enclave of another constituency
- Compactness - We want the constituency to be roundish
- Convexity - We want the constituency to have a convex shape
- Relevance - We want the assigned name of the constituency to reflect its location

Please refer to [scoring.md](./SCORING.md) for a detailed explanation.

## Sources

The 2025 polling districts `raw_data/ge2025_polling_districts.kml` are annotated by Yudhishthra Nathan and Goh Tiong Ann.
They were published at https://www.facebook.com/yudhishthra/posts/pfbid02SgcvubpES3Rh7ht32qjCc4KCUCMRbwe5ozvpBu6kx2uUHioQy4HtYd6bBhevhjLKl
and on https://www.google.com/maps/d/u/0/viewer?mid=1FT8Te1iDvt4gNHZh2h6tLh7sDv_UkUg. I have made edits to the polling districts to improve correctness.


The 2025 elector sizes `raw_data/ge2025_electoral_divisions_and_polling_districts.json` 
and district allocation `raw_data/ge2025_polling_districts_and_elector_size.json`
are processed from The Report of the Electoral Boundaries Review Committee https://www.eld.gov.sg/pdf/White_Paper_on_the_Report_of_the_Electoral_Boundaries_Review_Committee_2025.pdf.


The MRT station coordinates `raw_data/stations.csv` are processed from https://en.wikipedia.org/wiki/List_of_Singapore_MRT_stations.
The MRT passenger volume data can be found at https://datamall.lta.gov.sg/content/datamall/en/dynamic-data.html "Passenger Volume by Train Stations".


## Inaccuracies

Polling district elector sizes are all estimates.
The Report of the Electoral Boundaries Review Committee documented the elector size of various sets of polling districts in Annex B.
For every set of polling districts, I assumed each polling district has approximately the same elector size to estimate the elector size of each polling district.
