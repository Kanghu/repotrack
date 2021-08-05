/***
	This script handles the aggregation methods for collected metrics.
***/

Configs = [".xml", ".yaml", ".md", ".gitignore", ".ini", ".cfg", ".json"]

// Compute aggregated metrics for a certain contributor
function computeAggregatedMetrics(contribution_map_self, contribution_map_all) {
	metrics = {}

	// Aggregation methods
	const fwd = function(loc, func) { return loc+func }
	const re = function(func_1, func_2) { return func_1 + func_2 }
	const man = function(com, loc) { return com+loc }

	//
	cfg_sum_self = Object.keys(contribution_map_self).filter(k => Configs.includes(k)).map(k => contribution_map_self[k]).reduce((a, b) => a + b, 0)
	cfg_sum_all = Object.keys(contribution_map_all).filter(k => Configs.includes(k)).map(k => contribution_map_all[k]).reduce((a, b) => a + b, 0)

	// Call the methods defined above on given parameters
	metrics['Engineering'] = fwd(contribution_map_self['LOC+'], contribution_map_self['FUNC+']) / fwd(contribution_map_all['LOC+'], contribution_map_all['FUNC+'])
	metrics['Re-engineering'] = re(contribution_map_self['FUNC+'], contribution_map_self['FUNC*']) / re(contribution_map_all['FUNC+'], contribution_map_all['FUNC*'])
	metrics['Management'] =
		man(contribution_map_self['COM+'], cfg_sum_self) / man(contribution_map_all['COM+'], cfg_sum_all)

	return metrics
}

// Compute statistics describing the distribution of work
function computePackageStats(node) {
	// Variables for counting children & computing the average
	avg = {}
	children = node.children ? node.children : node._children
	len_childs = children.length

	// Parse all childs objects of this node
	for(i=0; i<children.length; i++) {
			contrib = {}
			top10 = node.contributors.length / 10

			// Collect the summed contribution map for all contributors according to selected time mode
			all_contribution_map = null;
			if(timeMode == 'recent') {
				all_contribution_map = children[i].contributors.filter(c => c.name == 'All').map(c => c.contrib_recent)[0]
				children[i].contributors.sort((a, b) => (a.contrib_recent['LOC+'] > b.contrib_recent['LOC+']) ? -1 : 1)
			} else {
				all_contribution_map = children[i].contributors.filter(c => c.name == 'All').map(c => c.contrib)[0]
				children[i].contributors.sort((a, b) => (a.contrib['LOC+'] > b.contrib['LOC+']) ? -1 : 1)
			}

			// Parse the top-10% contributors of this node
			for(j=1; j<1+Math.min(node.contributors.length-1, Math.ceil(top10)); j++) {
					if(j >= children[i].contributors.length) break;
					else if(children[i].contributors[j] == undefined) continue;

					contribution_map = null
					if(timeMode == 'recent') {
							contribution_map = children[i].contributors[j].contrib_recent
					} else {
							contribution_map = children[i].contributors[j].contrib
					}

					for(const stat in contribution_map) {
							if(!(stat in contrib)) {
								contrib[stat] = 0.0
							}

							// We check for NaN values beforehand
							self_term = contribution_map[stat] != NaN ? contribution_map[stat] : 0;
							all_term = all_contribution_map[stat] != NaN ? all_contribution_map[stat] : 0;
							contrib[stat] += 1.0 * (self_term) / (all_term > 0 ? all_term : 1)
					}
			}

			if(contrib['LOC+'] == 0) {
				len_childs -= 1
			}

			// Store the running average for each children
			for(const stat in contrib) {
					if(!(stat in avg)) {
						avg[stat] = 0.0
					}

					avg[stat] += contrib[stat]
			}

	}

	// Divide back to obtain average
	for(const stat in avg) {
			avg[stat] = avg[stat] / len_childs
			avg[stat] = avg[stat] * 100.0

			if(avg[stat] > 100.0) {
				// Malformed calculation, totals cannot exceed 100%
				avg[stat] = 100.0
			}
	}
	
	console.log(avg)
	return avg
}
