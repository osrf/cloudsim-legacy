var time_window_secs = 30;
var min_color  = "#4DA74D"; // rgb(77,167,77); green
var max_color  = "#CB4B4B"; // rgb(203,75,75); red
var avg_color  = "#AFD8F8"; // rgb(175,216,248); blue 
var mdev_color = "#EDC240"; // rgb(237,194,64); yellow
var latency_data = {};



function create_latency_widget(machine_div, 
                               constellation_name, 
                               machine_name,
                               data_key)
{
	var unique_plot_id = "latency_"+machine_name;
	var widget_div = _create_empty_widget(machine_div, unique_plot_id);
	widget_div.style.height = "150px";
	
    var latency_plot_data = [   
                             { label:"min", color: min_color, data:[] }, 
                             { label:"max", color: max_color, data:[]}, 
                             { label:"average", color:avg_color, data:[]} 
                         ];


    var plot_options = {

    		// yaxis: {
    		//        min: 0,
    		//max: 110
    		//    },

    		xaxis: { 
    			// font: null,
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
    
  

    // var j_plot = $.plot($('#' + plot_div_name), latency_plot_data, plot_options);
    latency_data[unique_plot_id] = { 'plot_data': latency_plot_data,
    		// 'plot' : j_plot,
    		'plot_options' : plot_options,
    		'last_update' : null};
    
    $.subscribe("/constellation", function(event, data){
    	if(data.constellation_name != constellation_name)
    		return;
    	
    	
    	var values_str = data[data_key];
//    	console.log(values_str);
    	var values = eval(values_str)
//    	console.log(values.length)
   	
    	var latency_plot_data = latency_data[unique_plot_id]['plot_data'];
    	_set_latency_data(latency_plot_data, values);
    	
        var plot_options = latency_data[unique_plot_id]['plot_options']
        document.getElementById(unique_plot_id).innerHTML = "";
        latency_data[unique_plot_id]['plot'] = $.plot($('#' + unique_plot_id), latency_plot_data, plot_options);

    });
}


function _set_latency_data(latency_plot_data, values)
{
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

/* 
function _update_graph(plot_div_name, constellation_name, machine_name, min, max, avg, mdev)
{
	var unique_plot_id = "latency_"+machine_name;
    
    var latency_plot_data = latency_data[unique_plot_id]['plot_data'];
    var last_update = latency_data[unique_plot_id]['last_update'];
    var t = Date.now() * 0.001;
    latency_data[unique_plot_id]['last_update'] = t;
    
    
    add_latency_widget_sample(latency_plot_data, t, last_update , min, max, avg, mdev);
    
    
    var plot_options = latency_data[unique_plot_id]['plot_options']
    document.getElementById(unique_plot_id).innerHTML = "";
    latency_data[unique_plot_id]['plot'] = $.plot($('#' + plot_div_name), latency_plot_data, plot_options);

}

function old_add_latency_widget_sample(latency_plot_data, t, last_update, 
									min_latency_sample, max_latency_sample, avg_sample, mdev_sample)
{
    var elapsed = 0;

    if(last_update) 
        elapsed = t - last_update;

    last_update = t;

    var first_fresh_data = 0;

    var min_latency = latency_plot_data[0].data;
    var max_latency = latency_plot_data[1].data;
    var avg = latency_plot_data[2].data;
    
    
//   var mdev = latency_plot_data[3].data;


    min_latency.push( [0,min_latency_sample] ); 
    max_latency.push( [0,max_latency_sample]);
    avg.push ( [0, avg_sample ]);
//    mdev.push( [0, mdev_sample ]); 

    // adjust values by aging:
    for (var i = 0; i < avg.length-1; i++)
    {
        var t = avg[i][0] + elapsed;
  
        min_latency[i][0] = t;
        max_latency[i][0] = t;
        avg[i][0] = t;
//        mdev[i][0] = t;

        if(t > time_window_secs)
        {
            first_fresh_data = i;
        }
    }
     
    // remove old data
    min_latency = min_latency.slice(first_fresh_data);
    max_latency = max_latency.slice(first_fresh_data);
    avg = avg.slice(first_fresh_data);
//  mdev = mdev.slice(first_fresh_data);   

}
*/
