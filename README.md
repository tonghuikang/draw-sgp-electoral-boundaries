# Evaluating and Assigning Singapore Constituencies

## How to evaluate constituency assignment

We assume that we are given the polling districts and we cannot change them.

The task of drawing the electoral boundaries is to assign constituencies names and polling districts.

For each constituency, we can measure how good they are
- Electoral balance - We want the elector per member is close to the mean
- Nonenclavity - We do not want constituencies that are an enclave of another constituency
- Compactness - We want the constituency to be roundish
- Convexity - We want the constituency to have a convex shape
- Relevance - We want the assigned name of the constituency to reflect its location


## Sources

The 2025 polling districts `raw_data/ge2025_polling_districts.kml` is annotated by Yudhishthra Nathan et al.
It was published at https://www.facebook.com/yudhishthra/posts/pfbid02SgcvubpES3Rh7ht32qjCc4KCUCMRbwe5ozvpBu6kx2uUHioQy4HtYd6bBhevhjLKl
on https://www.google.com/maps/d/u/0/viewer?mid=1FT8Te1iDvt4gNHZh2h6tLh7sDv_UkUg


The 2025 elector sizes `raw_data/ge2025_electoral_divisions_and_polling_districts.json` 
and district allocation `raw_data/ge2025_polling_districts_and_elector_size.json`
is processed from https://www.eld.gov.sg/pdf/White_Paper_on_the_Report_of_the_Electoral_Boundaries_Review_Committee_2025.pdf


The MRT station coordinates `raw_data/stations.csv` is processed from https://en.wikipedia.org/wiki/List_of_Singapore_MRT_stations


## Inaccuracies

There are some inaccuracies in the polling districts. I will live with them for now.

- NS21 should be carved from NS19
- SK18 should be carved from SK17


Polling district elector sizes are all estimates.


