var time_window_secs = 30;
var min_color  = "#4DA74D"; // rgb(77,167,77); green
var max_color  = "#CB4B4B"; // rgb(203,75,75); red
var avg_color  = "#AFD8F8"; // rgb(175,216,248); blue 
var mdev_color = "#EDC240"; // rgb(237,194,64); yellow

var latency_data = {};

var last_update = null;

function add_latency_sample(latency_plot_data, t, min_latency_sample, max_latency_sample, avg_sample, mdev_sample)
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




