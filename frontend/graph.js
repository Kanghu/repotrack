
// ************** Method for initializing DOM *****************************
function init_DOM() {
	// Initialize radio button listeners
	var radios = document.getElementsByName("mode");
	for (var i = 0; i < radios.length; i++) {
	    radios[i].addEventListener('change', function() {
	        graphMode = this.value
	    });
	}

	var radios = document.getElementsByName("time");
	for (var i = 0; i < radios.length; i++) {
	    radios[i].addEventListener('change', function() {
	        timeMode = this.value
	    });
	}

	// Initialize on upload event listener
	const inputElement = document.getElementById("input");
	inputElement.addEventListener("change", handleFiles, false);

	function handleFiles() {
	  const fileList = this.files[0];
	  var reader = new FileReader();
	  reader.onload = function(e) {
	    treeData = [JSON.parse(e.target.result)]

		root = treeData[0];
		root.x0 = height / 2;
		root.y0 = 0;

		update(root);

		var nodes = tree.nodes(root)
		var width = tree.nodeSize()[0] * nodes.length;
		var height = tree.nodeSize()[1] * nodes.length;

		d3.select('#container').select('svg')
		   .attr("width", width)
		   .attr("height", height)

		d3.select('#container').select('svg').select('g')
		   .attr("transform", "translate(" + width/2 + "," + height/2 + ")");

		var offset_x = 400, offset_y = 300
		document.getElementById('container')
			.scrollTo(width/2 - offset_x, height/2 - offset_y)

		 collapseAll();
	  };

	  reader.readAsText(this.files[0]);
	}
}

function update(source) {
  // Compute the new tree layout.
  var nodes = tree.nodes(root).reverse(),
	  links = tree.links(nodes);

  // Normalize for fixed-depth.
  nodes.forEach(function(d) { d.y = d.depth * 180; });

  // Update the nodes…
  var node = svg.selectAll("g.node")
	  .data(nodes, function(d) { return d.id || (d.id = ++i); });

  // Enter any new nodes at the parent's previous position.
  var nodeEnter = node.enter().append("g")
	  .attr("class", "node")
	  .attr("transform", function(d) { return "translate(" + source.y0 + "," + source.x0 + ")"; })
	  .on("click", click);

  nodeEnter.append("circle")
	  .attr("r", 1e-6)
	  .style("fill", function(d) { return d._children ? "lightsteelblue" : "#fff"; });

  nodeEnter.append("text")
	  .attr("x", function(d) { return d.children || d._children ? -15 : 15; })
	  .attr("dy", ".35em")
	  .attr("text-anchor", function(d) { return d.children || d._children ? "end" : "start"; })
	  .text(function(d) { return d.name; })
	  .style("fill-opacity", 1e-6);

  // Transition nodes to their new position.
  var nodeUpdate = node.transition()
	  .duration(duration)
	  .attr("transform", function(d) { return "translate(" + d.y + "," + d.x + ")"; });

  nodeUpdate.select("circle")
	  .attr("r", 10)
	  .style("fill", function(d) { return d._children ? "lightsteelblue" : "#fff"; });

  nodeUpdate.select("text")
	  .style("fill-opacity", 1);

  // Transition exiting nodes to the parent's new position.
  var nodeExit = node.exit().transition()
	  .duration(duration)
	  .attr("transform", function(d) { return "translate(" + source.y + "," + source.x + ")"; })
	  .remove();

  nodeExit.select("circle")
	  .attr("r", 1e-6);

  nodeExit.select("text")
	  .style("fill-opacity", 1e-6);

  // Update the links…
  var link = svg.selectAll("path.link")
	  .data(links, function(d) { return d.target.id; });

  // Enter any new links at the parent's previous position.
  link.enter().insert("path", "g")
	  .attr("class", "link")
	  .attr("d", function(d) {
		var o = {x: source.x0, y: source.y0};
		return diagonal({source: o, target: o});
	  });

  // Transition links to their new position.
  link.transition()
	  .duration(duration)
	  .attr("d", diagonal);

  // Transition exiting nodes to the parent's new position.
  link.exit().transition()
	  .duration(duration)
	  .attr("d", function(d) {
		var o = {x: source.x, y: source.y};
		return diagonal({source: o, target: o});
	  })
	  .remove();

  // Stash the old positions for transition.
  nodes.forEach(function(d) {
	d.x0 = d.x;
	d.y0 = d.y;
  });
}

function toggle(d) {
	d.children = d._children;
	d._children = null;
}

// Toggle children on click.
function click(d) {
	if (d.children) {
		d._children = d.children;
		d.children = null;
	} else {
		d.children = d._children;
		d._children = null;

		if(d.children != undefined && d.children.length == 1) {
			toggle(d.children[0])
		}
	}
	update(d);

	// Show contributions
	togglePanel(d);
	toggleCohesionChart(barSvg, computePackageStats(d));

	// Update the current selection variables
	currentNode = d.name
	if(currentPanel == 'metric') {
		toggleStat(d.contributors, currentSelection)
	}
	document.getElementById('repo-name').innerHTML = currentNode
}

/* Collapse a specific node */
function collapse(d) {
  if (d.children) {
    d._children = d.children;
    d._children.forEach(collapse);
    d.children = null;
  }
}

/* Collapse the entire tree */
function collapseAll(){
    root.children.forEach(collapse);
    collapse(root);
    update(root);
}

/* Refresh the sidepanel upon focusing on a specific node */
function togglePanel(d) {
	var stats = d3.entries(d.contributors[0].contrib).map(e => e.key)
	var contributorNames = d.contributors.filter(c => c.name != 'All').map(d => d.name)
	var contributors = d.contributors
	var ul = d3.select('#panel').select('ul')
	var statUl = d3.select('#panel').select('#stat-ul')

	stats = stats.filter(s => contributors.map(c => c.contrib[s]).reduce((a, b) => a + b, 0) > 0)

	if(timeMode == 'recent') {
		contributors = contributors.filter(c => Object.values(c.contrib_recent).reduce((a, b) => a + b, 0) > 0)
	}

	document.getElementById('contributors-h').innerHTML = "Contributors (" + contributors.length.toString() + "):"
	document.getElementById('metrics-h').innerHTML = "Metrics (" + stats.length.toString() + "):"

	/* Clean up previous <li> */
	ul.selectAll('li')
	.remove()
	statUl.selectAll('li')
	.remove()

	ul.selectAll('li')
	.data(contributors)
	.enter()
	.append('li')
	.attr('class', 'name-label')
	.html(function(c) {return c.name})
	.on("click", function(c) {return toggleContributor(c, contributors)});

	statUl.selectAll('li')
	.data(stats)
	.enter()
	.append('li')
	.attr('class', 'name-label')
	.text(function(c) {return c})
	.on("click", function(c) {return toggleStat(contributors, c)});
}

function toggleContributor(contributor, contributors) {
	currentPanel = 'contributor'

	// Process data => Split into direct/aggregated metrics
	if(timeMode == 'all') {
		contrib = contributor.contrib
	} else {
		contrib = contributor.contrib_recent
	}
	barData = d3.entries(contrib);

	// Filter out values
	barData = barData.filter(b => !AggregatedMetrics.includes(b.key))
	barData = barData.filter(d => d.value != 0 && d.value != 0.0)

	// Collect the 'All' contributor
	all = d3.entries(contributors.filter(c => c.name == 'All').map(c => c.contrib)[0])
	barData.forEach(function(d) {
		d.key = d.key;
		d.value = +d.value;

		// Transform data if mode is 'weighted'
		if(graphMode == 'weighted') {
			all_stat = all.filter(c => c.key == d.key)[0]
			if(all_stat != undefined) {
				d.value = (+(d.value) / +(all_stat.value)) * 100
			}
		}
	});

	prepareChart(barSvg, barData)
	toggleAggregationChart(chartSvg, computeAggregatedMetrics(contributor.contrib, contributors.filter(c => c.name == 'All')[0].contrib))

	if(barData.length == 0) {
		// Add text describing empty graph
		barSvg.append("g")
			.attr("transform", "translate(-25,-25)")
		.append("text")
			.style("font-size", "16px")
			.text("Nothing to show");
	}
}

function toggleStat(contributors, stat) {
	currentPanel = 'metric'
	currentSelection = stat
	// Collect this specific contribution from all given contributors
	contrib = []
	for(i=0; i<contributors.length; i++) {
		c = contributors[i]

		if(timeMode == 'recent') {
			entries = d3.entries(c.contrib_recent)
		} else {
			entries = d3.entries(c.contrib)
		}
		contrib[i] = {}
		contrib[i].key = c.name;
		contrib[i].value = 0;
		contrib[i].value += entries.filter(e => e.key == stat).map(e => e.value)[0];
	}

	barData = contrib;
	// Collect the 'All' contributor
	all = barData.filter(c => c.key == 'All').map(c => c.value)[0]
	barData.forEach(function(d) {
		d.key = d.key;
		d.value = +d.value;

		// Transform data if mode is 'weighted'
		if(graphMode == 'weighted') {
			d.value = (+(d.value) / +(all)) * 100
		}
	});

	if(graphMode == 'weighted') {
		barData = barData.filter(c => c.key != 'All')
	}

	barData.sort((a, b) => (a.value > b.value) ? -1 : 1)
	barData = barData.slice(0, 12)

	prepareChart(barSvg, barData)
}

function toggleCohesionChart(chart, contribution) {
	// Process data
	barData = d3.entries(contribution)
	barData.forEach(function(d) {
		d.key = d.key;
		d.value = +d.value;
	});

	prepareChart(chart, barData)

	// Specify how the X axis should be rendered
	chart.append("g")
		.attr("transform", "translate(-25,-25)")
	.append("text")
		.style("font-size", "16px")
		.text("Avg. contribution of top 10% developers within this package");
}

function toggleAggregationChart(chart, data) {
	// Process data
	barData = d3.entries(data)
	barData.forEach(function(d) {
		d.key = d.key;
		d.value = +d.value;
	});

	prepareChart(chart, barData)

	// Specify how the X axis should be rendered
	chart.append("g")
		.attr("transform", "translate(-25,-25)")
	.append("text")
		.style("font-size", "16px")
		.text("Aggregated contribution of selected contributor:");
}


/***
	Prepare the given chart for visually displaying the passed data.
	Data will be visualized as a bar chart with 2 axis.
***/
function prepareChart(chart, data) {
	// Clean the SVG
	chart.selectAll("*").remove()

	// Scale the range of the data
	y.domain(barData.map(function(d) { return d.key; }));
	x.domain([0, d3.max(barData, function(d) { return d.value; })]);

	// Specify how the X axis should be rendered
	chart.append("g")
		.attr("class", "y axis")
		.call(yAxis)
	.append("text")
		.attr("transform", "rotate(-90)")
		.attr("dy", ".71em")
		.style("text-anchor", "end");

	// Specify how the Y axis should be rendered
	chart.append("g")
		.attr("class", "x axis")
		.attr("transform", "translate(0," + panelHeight / 2 + ")")
		.call(xAxis)
	.selectAll("text")
		.style("text-anchor", "end")
		.attr("dx", "+.15em")
		.attr("dy", "+.85em")
		.attr("transform", "rotate(-45)" );
		
	colour = d3.entries(StatColors)

	// Add the coloured bar charts
	chart.selectAll("bar")
		.data(barData)
	.enter().append("rect")
		.attr("class", "bar")
		.attr("y", function(d) { return y(d.key) })
		.attr("width", function(d) { return x(d.value); })
		.attr("x", function(d) { return 0; })
		.attr("height", y.rangeBand())
		.attr("fill", "lightblue")
		.attr("fill", 
			function(d) { 
				if(colour.filter(e => e.key == d.key).length > 0) {
					return colour.filter(e => e.key == d.key).map(e => e.value)[0];
				} else {
					return "cornflowerblue";
				}
			}
		);
		

}
