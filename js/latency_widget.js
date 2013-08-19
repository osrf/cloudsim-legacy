var time_window_secs = 30;
var min_color  = "#4DA74D"; // rgb(77,167,77); green
var max_color  = "#CB4B4B"; // rgb(203,75,75); red
var avg_color  = "#AFD8F8"; // rgb(175,216,248); blue 
var mdev_color = "#EDC240"; // rgb(237,194,64); yellow
var latency_data = {};



function create_latency_widget(machine_div, 
                               constellation_name, 
                               machine_name,
                               data_key,
                               title,
                               max_value)
{
    var unique_plot_id = "latency_"+ constellation_name + "_" + machine_name;
    var widget_div = _create_empty_widget(machine_div, unique_plot_id);
    widget_div.style.height = "150px";
    
    // Set widget's title
    var title_div = document.createElement("div")
    title_div.setAttribute("id", "latency_" + machine_name + "_title");
    title_div.setAttribute("style", "width:800px; padding: 10px 0px 0px 17px; position: relative;");
    title_div.innerHTML = "<b>" + title + "</b>";
    widget_div.parentElement.insertBefore(title_div, widget_div);

    var latency_plot_data = [   
                             { label:"min", color: min_color, data:[] }, 
                             { label:"max", color: max_color, data:[]}, 
                             { label:"average", color:avg_color, data:[]} 
                         ];
    
    // how to display the decimal values on
    // the y axis
    var decimal_places = 0;
    if (max_value < 100)
    {
    	decimal_places = 2;
    }
    	
    var plot_options = {

    		yaxis: {
    		        min: 0,
    		        max: max_value,
    		        tickFormatter : function (v, yaxis) 
        			{ 
        				//var v = (xaxis.max -v);   
        				var str = v.toFixed(decimal_places) + " ms"; 
        				return  str;
        			}
    		   },

    		xaxis: { 
    			// font: null,
    			axisLabel: 'Round trip latency',
    			min: 0,
    			max: 30,
    			tickFormatter : function (v, xaxis) 
    			{ 
    				//var v = (xaxis.max -v);   
    				var str = v.toFixed(0) + " s"; 
    				return  str;
    			},
    			transform: function (v) { return -v; },
    			inverseTransform: function (v) { return -v; }
    		},

    		legend: {
    			show: false
    		} ,

    		grid: {
    			borderWidth: 1,
    			minBorderMargin: 20,
    			labelMargin: 10,
    			backgroundColor: {
    				colors: ["#fff", "#e4f4f4"]
    			},
    			hoverable: true,
    			mouseActiveRadius: 50,
    			margin: {
    				top: 8,
    				bottom: 20,
    				left: 20
    			},
    			markings: function(axes) {
    				var markings = [];
    				var xaxis = axes.xaxis;
    				for (var x = Math.floor(xaxis.min); x < xaxis.max; x += xaxis.tickSize * 2) {
    					markings.push({ xaxis: {from: x, to: x + xaxis.tickSize }, color: "rgba(232, 232, 255, 0.2)" });
    				}
    				return markings;
    			}

    		}
    };
    
    var plot = $.plot($('#' + unique_plot_id), latency_plot_data, plot_options);

    // var j_plot = $.plot($('#' + plot_div_name), latency_plot_data, plot_options);
    latency_data[unique_plot_id] = { 'plot_data': latency_plot_data,
    		// 'plot' : j_plot,
    		'plot_options' : plot_options,
    		'last_update' : null};
    
    var current_title = "";
    $.subscribe("/constellation", function(event, data){
    	if(data.constellation_name != constellation_name)
    		return;
    	
    	
    	var values_str = data[data_key];
//    	console.log(values_str);
    	var values = eval(values_str)
//    	console.log(values.length)
   		
    	try
    	{
        	var avg_latency = values[0][2];
        	var str = avg_latency.toFixed(3) + " ms"; 
        	var txt = "<b>" + title  +" [" + str + "]"+ "</b>";
        	
        	if(current_title != txt)
        	{
        		title_div.innerHTML = txt;
        	}
        	current_title = txt;
    	}
    	catch(err)
    	{
    		title_div.innerHTML = "<b>" + title + "</b>";
    	}
    	
    	var latency_plot_data = latency_data[unique_plot_id]['plot_data'];
    	_set_latency_data(latency_plot_data, values);
    	
        var plot_options = latency_data[unique_plot_id]['plot_options']
        //document.getElementById(unique_plot_id).innerHTML = "";
        // latency_data[unique_plot_id]['plot'] =  $.plot($('#' + unique_plot_id), latency_plot_data, plot_options);
        plot.setData(latency_plot_data);
        //plot.setupGrid();
         
        plot.draw();
    });
}


function _set_latency_data(latency_plot_data, values)
{
	if (values == undefined)
	{
		return;
	}
	if(values.length ==0)
		return;
	
    var min_latency = [];
    var max_latency = [];
    var avg = [];
   
    var t_latest = values[0][0];
    for (var i = values.length-1; i >=0 ; i--)
    {	
    	var t_value = values[i][0];
    	var min = values[i][1];
    	var max = values[i][2];
    	var ave = values[i][3];
    	var t = t_latest - t_value;
        min_latency.push( [t,min] ); 
        max_latency.push( [t,max]);
        avg.push ( [t, ave ]);
    }
    latency_plot_data[0].data = min_latency;
    latency_plot_data[1].data = max_latency;
    latency_plot_data[2].data = avg;
}


