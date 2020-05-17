# Drawing Singapore's Electoral Boundaries

What has been done - data preprocessing

- (done) Obtain the zoning data.
- (done) Identify which subzone is adjacent to which subzone.
- (done) Construct the graph of the subzone and visualise it
- The data should be sufficient, but I appreciate more granular popluation information.

## TODO
Mathematical modelling

- Define the loss function, and constraints.
- Define the mathematical problem (linear programming)?
- Construct a draft solution and devise a function to calculate the loss.
- Construct an algorithmic solution to determine the optimal distribution.
- Display the solution.

Deployment

- Front-end development to produce an interactive interface of drawing electoral boundaries.

![image](https://i.imgur.com/piOHlGT.jpg)

## Data sources

https://www.eld.gov.sg/pdf/White%20Paper%20on%20the%20Report%20of%20the%20Electoral%20Boundaries%20Review%20Committee%202015.pdf
Contains the visulisation as shown above. You can see that each electorate is made up of subzones.



https://www.google.com.sg/maps/d/viewer?ll=1.315521116399046%2C103.8463351752846&z=11&mid=1p4VfSRkaNZViwdsr-KRvpiEjQESuP3vP Polling districts from https://www.facebook.com/pritam.eunos/posts/2972177026137924

<iframe src="https://www.google.com.sg/maps/d/embed?mid=1p4VfSRkaNZViwdsr-KRvpiEjQESuP3vP&z=10" width="640" height="480"></iframe>

https://data.gov.sg/dataset/electoral-boundary-2015
Electoral boundary datapoints in 2015.

Planning area/subzone based on URA MP14, Singapore Residents by Subzone and Type of Dwelling, Jun 2017
https://data.gov.sg/dataset/singapore-residents-by-subzone-and-type-of-dwelling-jun-2017
This is the latest data that I have - this is how it looks like when uploaded to Google Maps https://drive.google.com/open?id=1WCq8jMEkWFeaoDDA5hboony-Rf_0LuLr&usp=sharing

## Commentaries
https://newnaratif.com/research/how-gerrymandering-creates-unfair-elections-in-singapore/
http://www.wp.sg/wp-statement-on-ebrc-report-dated-13-mar-2020/

Still trying to find a statement where WP say they want a method of drawing the electoral boundaries neutrally.

## Algorithmic sources

https://github.com/pnklein/district
No explaination I don't know how to use.

https://www.youtube.com/watch?v=NAS4AsPi1q4
Random monkey drawing to test if a particular drawing is politically biased.

https://www.youtube.com/watch?v=Mv9kscNo5Gc
Similar ideas.

https://www.todayonline.com/singapore/whos-electoral-boundaries-review-committee-and-how-it-draws-ge-battle-lines
In 2015, the EBRC determined that one MP could represent between 20,000 and 37,000 voters. It also had to be mindful that the GRCs with fewer MPs should not have more electors than a GRC with more MPs.

https://stackoverflow.com/questions/33782390/how-to-divide-a-connected-weighted-graph-to-n-semi-equal-subgraphs
This is a minimum k-cut problem.

https://en.wikipedia.org/wiki/Stoer–Wagner_algorithm
For a minimum 2-cut in an unweighted grpah

Min-cost flow - https://developers.google.com/optimization/flow/mincostflow However, 

Degree-constrained minimum spanning tree https://en.wikipedia.org/wiki/Degree-constrained_spanning_tree

Polynomial algorithm to compute N+1 degree https://www.sciencedirect.com/science/article/pii/S019667748471042X?via%3Dihub

Approximate algorithm to compute an suboptimal solution to an arbitrary degree https://github.com/niroyb/AntBased_DCMST



## The special case of Singapore

There are work done by other academics on how to draw their electoral bounadaries. However, such methods cannot be immediately applied to Singapore due to some difference in election rules. Let us review Singapore's system:

#### Division by polling districts.

The smallest unit of electorate division is by polling district. Usually, the boundaries of these districts cut through roads, so that adjcent housing block remain in the same polling district.

The polling districts are likely to remain the same unless major changes are made to the neighbourhood (for example completion of a cluster of residental housing). As these polling districts are usually small, it is usually defined by the Singapore's land agency as a given input to our electoral boundary drawing.

#### GRC and SMC. 

While the electorate represented per seat is within a limit, the size of the constituency can be different by multiples. 
In Singapore there are two types of constitutencies, Group Representation Constituency and Single Member Constituency. 

The size of GRC can range to 3-member GRC to 6-member GRC. Each GRC needs to field a minority candidate. You may read up on the justifiation, praise and criticism of this system. The number and size of GRC is likely to have been decided to by the prime minister before the nomination for the election.

So the task is to divide the polling districts into a set number of SMC and GRC (of respective sizes).

#### Area names.

Unlike other countries, SMC and GRC has a name. Each constituency is not merely a number like "North Carolina 12th Congressional District". People and policitians associate themselves to the place or town.

However, when do you consider yourself to be part of a town or otherwise? One way is to look at the road name. If you live on Ang Mo Kio Avenue 1 you will consider weird to be assigned to Nee Soon GRC. 

#### Past constituency.

It is also best to keep constituencies the same as it was in the past. Even if the reassignment of a polling district produces fairer configuration, there will still be sentiments on whether this reassignment benefit a certain political party.


## The formalised problem

When you reduce a problem to mathematics, you have access to a range of mathematical tools which you can apply to the problem.

Each polling district will be represented as a node in a connected graph. Adjenct districts are connected with an edge. 


### Objective

We want a fair assignment of the constituencies. 
The problem is to partition the graph. However, as constituency names need to be assigned.
Constraints must be respected, and losses will be assigned for ineffencies.

### Constraints

- Constituencies must be contiguous
- The number of residents per seat must be within a certain range
- Number of GRCs and SMCs should be equal to what was defined

### Losses

- Assigning a constituency name that is different from the area name
- Historical constituencies, when constituencies change people complain as well.
- Parameters. We penalise constituencies with less circular shape.

## Approaches

This is not merely a partitioning problem, because it involves assigning tags to polling district.

#### Linear programming

You have an array of tags against polling district. 1 indicates that the tag is assigned to the polling district, 0 otherwise. Conditions and losses are imposed.

#### Random monkey

You start with a not-so-random initial state - for instance one assigned with default names, or the previous year's constituencies. Then small modifications are made to see if provides a fairer assignment.

## Additional data appreciated

- The population of each polling district. This is the actual input that is used to draw the electoral boundaries, rather than subzones
- The result of each polling district. This will not be used as an input in any form. It is meant to measure the outcome of elections if boundaries have been drawn differently.

## Support me!

Buy me a coffee at Cantonment Road!
