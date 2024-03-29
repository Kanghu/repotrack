/***
	This represents the main script of the frontend, responsible for initializing the
	D3.js library and setting up the graphical devices (collapsible tree, barcharts)
	that we are employing in our application
***/


// *************** Global variables **********************
var graphMode = 'weighted'
var timeMode = 'all'
var currentPanel = 'metric'
var currentSelection = ''
var currentNode = ''

var AggregatedMetrics = ["Engineering", "Re-engineering", "Management"]

/* Color pallete for bar chart statistics */
var StatColors = {
	"LOC+":"rgb(55,126,184)",
	"LOC-":"rgb(228,26,28)",
	"FUNC+":"rgb(77,175,74)",
	"FUNC-":"rgb(152,78,163)",
	"COM+":"rgb(255,127,0)",
	"COM-":"rgb(255,255,51)",
	"FUNC*":"rgb(166,86,40)",
	"<ModificationType.ADD: 1>":"rgb(247,129,191)",
	"<ModificationType.MODIFY: 5>":"rgb(106,61,154)",

	"Engineering":"rgb(27,158,119)",
	"Re-engineering":"rgb(217,95,2)",
	"Management":"rgb(117,112,179)"
}

/* Some sample data.. */
var treeData =
[
	{
		"name":"huh",
		"contributors":[
			{
				"name":"All",
				"contrib":{
				    "LOC+": 799,
					"LOC-": 40,
					"FUNC+": 24,
					"FUNC-": 0,
					"COM+": 4796,
					"COM-": 11
				}
			},
			{
				"name":"Jacob",
				"contrib":{
				    "LOC+": 799,
					"LOC-": 40,
					"FUNC+": 24,
					"FUNC-": 0,
					"COM+": 4796,
					"COM-": 11
				}
			}
		],
		"children":[
			{
				"name":"lol",
				"contributors":[
					{
						"name":"All",
						"contrib":{
								"LOC+": 800,
							"LOC-": 41,
							"FUNC+": 25,
							"FUNC-": 1,
							"COM+": 4797,
							"COM-": 12
						}
					},
					{
						"name":"Jacob",
						"contrib":{
								"LOC+": 450,
							"LOC-": 40,
							"FUNC+": 24,
							"FUNC-": 0,
							"COM+": 4796,
							"COM-": 11
						}
					},
					{
						"name":"smth",
						"contrib":{
								"LOC+": 350,
							"LOC-": 1,
							"FUNC+": 1,
							"FUNC-": 1,
							"COM+": 1,
							"COM-": 1
						}
					}
				]
			}
		]
	}
]

// Initialize DOM elements (fileHandler, radio listeners)
init_DOM()

// ************** Generate the tree diagram	 *****************
var margin = {top: 80, right: 100, bottom: 80, left: 100},
	width = 1600 - margin.right - margin.left;
	height =  1200 - margin.top - margin.bottom;

dx = 20;
dy = 40;

var i = 0,
	duration = 750,
	root;

var tree = d3.layout.tree()
	.nodeSize([dx, dy]);

var diagonal = d3.svg.diagonal()
	.projection(function(d) { return [d.y, d.x]; });

var svg = d3.select("#container").append("svg")
	.attr("width", width + margin.right + margin.left)
	.attr("height", height + margin.top + margin.bottom)
	.attr("class", "graph-svg")
  .append("g")
	.attr("transform", "translate(" + width/2 + "," + height/2 + ")");


root = treeData[0];
root.x0 = height / 2;
root.y0 = 0;

update(root);

d3.select(self.frameElement).style("height", "500px");

/*** Initialize the side panel (bar) ***/
var panelWidth = 750;
var panelHeight = 750;

var barSvg = d3.select("#panel").append("svg")
	.attr("width", panelWidth)
	.attr("height", panelHeight)
	.attr("class", "svg")
  .append("g")
	.attr("transform", "translate(" + 175 + "," + 75 + ")");


// Set the ranges
var x = d3.scale.linear().range([0, panelWidth / 2]);
var y = d3.scale.ordinal().rangeRoundBands([0, panelHeight / 2], .15);

// Define the axis
var xAxis = d3.svg.axis()
    .scale(x)
    .orient("bottom")

var yAxis = d3.svg.axis()
    .scale(y)
    .orient("left");

/*** Initialize second side panel (chart) ***/
var chartWidth = 750;
var chartHeight = 500;

var chartSvg = d3.select("#panel").append("svg")
	.attr("width", chartWidth)
	.attr("height", chartHeight)
	.attr("class", "svg")
  .append("g")
	.attr("transform", "translate(" + 150 + "," + 75 + ")");

toggleContributor(treeData[0].contributors[0].contrib, treeData[0].contributors)
collapseAll()
