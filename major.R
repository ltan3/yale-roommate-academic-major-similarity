library(plyr)
library(igraph)
library(reshape2)

data <- read.csv('ProjectDataMajor.csv')
major_names <- levels(as.factor(data$major))
rooms <- levels(as.factor(data$room))

### Count the number of each major for each year and across all years
majors_counts <- ddply(data, .(major, grad_year), nrow)
majors_counts_wide <- dcast(majors_counts, major ~ grad_year, value.var = 'V1', fill=0)
majors_counts_wide$total <- apply(majors_counts_wide[2:5], MARGIN = 1, sum)
write.csv(majors_counts_wide, 'counts.csv', row.names = F)


### Construct bipartite adjacency matrix of rooms v. majors
bipartite <- matrix(0, nrow = length(rooms), ncol=length(major_names))
colnames(bipartite) <- major_names

for (i in 1:nrow(data)) {
  room <- data[i,'room']
  major <- data[i,'major']
  bipartite[room, major] <- bipartite[room, major] + 1
}

bipartite_df <- data.frame(bipartite)
colnames(bipartite_df) <- major_names
bipartite_df$room <- rooms


### Create edge list
bipartite_el <- melt(bipartite_df, id.vars='room', variable.name = 'major', value.name='weight')
bipartite_el <- subset(bipartite_el, bipartite_el$weight > 0)
write.csv(bipartite_el, 'bipartite.el.csv', row.names = F)
# Add grad years for each room in Excel, saved as bipartite.el.csv


### Graph it
# transform for igraph
# el <- as.matrix(bipartite_el)
# g <- graph.edgelist(el[,1:2])
# E(g)$weight <- as.numeric(el[,3])
# plot(g,layout=layout.fruchterman.reingold,edge.width=E(g)$weight/2)


### Exclude standalone singles
suite_sum <- apply(bipartite, 1, sum)
bipartite_suite_df <- subset(bipartite_df, suite_sum >= 2)
bipartite_suite_el <- melt(bipartite_suite_df, id.vars='room', variable.name = 'major', value.name='weight')
bipartite_suite_el <- subset(bipartite_suite_el, bipartite_suite_el$weight > 0)
write.csv(bipartite_suite_el, 'bipartite.suites_only.el.csv', row.names = F)
## added years to bipartite.suites_only.el.csv in excel

### Calculate (unweighted) bipartite density for each grad year
bipartite <- read.csv('bipartite.suites_only.el.csv')
freshmen <- subset(bipartite, bipartite$year == 2022)
sophmores <- subset(bipartite, bipartite$year == 2021)
juniors <- subset(bipartite, bipartite$year == 2020)
seniors <- subset(bipartite, bipartite$year == 2019)

bipartite_density <- function(d) {
  nrooms <- length(unique(d$room))
  nmajors <- length(unique(d$major))
  graph <- graph_from_data_frame(d)
  nedges <- length(E(graph))
  nedges / nrooms / nmajors
}

bipartite_density(freshmen)
bipartite_density(sophmores)
bipartite_density(juniors)
bipartite_density(seniors)


### Collapse bipartite graph into graph of just majors v. majors of roommates
edges <- read.csv('bipartite.suites_only.el.csv')
j <- join(edges, edges, by = 'room', type='inner')
r <- j[,c(1,4,2,5)]
colnames(r) <- c('Room', 'Year', 'm1', 'm2')
r <- subset(r, r$m1 != r$m2)
write.csv(r, 'collapsed.el.csv', row.names = F)
# This includes two edges for each roommate pair (forward and backward). Delete the duplicate
# edges in excel.
# Split by year into four files collasped.el.YYYY.csv

