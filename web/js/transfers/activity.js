function initPage(graph,entity,src_filter,dest_filter,no_mss,period,upto)
{
  var jaxInput = {
    'url': dataPath + '/transfers/history',
    'data': { 'graph': graph,
	      'entity': entity,
	      'src_filter': src_filter,
	      'dest_filter': dest_filter,
	      'no_mss': no_mss,
	      'period': period,
	      'upto': upto
    },
    'dataType': 'json',
    'success': function (data, textStatus, jqXHR) { displayHistogram(graph,entity,data.data); },
    'error': handleError,
    'async': false
  };
  $.ajax(jaxInput);
}

function displayHistogram(graph,entity,data)
{
  // extract all other property information from the data block
  var dt = data[0].data[1].time*1000 - data[0].data[0].time*1000;
  var timing_string = data[0].timing_string;

  // get the plot data first
  var plot_data = [];
  for (var i_site in data) {
    var site_data = data[i_site].data;
    var plot_datum = {
      x: [],
      y: [],
      name: data[i_site].name,
      marker: {
  	opacity: 0.6,
  	line: {
  	  color: 'rbg(107,48,107)',
  	  width: 1.5,
  	}
      },
      type: 'bar',
    };
    for (var i in site_data) {
      var row = site_data[i];
      var date = new Date(row.time*1000); // input in epoch milliseconds
      date = date.getTime() + dt/2;

      var dateX = new Date(date);
      var size = row.size/1000/1000/1000;
      plot_datum.x.push(dateX);
      plot_datum.y.push(size);
    }
    plot_data.push(plot_datum);
  }

  // define the basic plot layout
  var basic_layout = {
    autosize: false, width: 900, height: 600,
    margin: { l: 80, r: 10, t: 40, b: 80 },
    title: '',
    titlefont: { family: 'Arial, sans-serif', size: 20, color: 'green' },
    showlegend: true,
    xaxis: {
      title: 'Time Axis',
      titlefont: { family: 'Arial, sans-serif', size: 24, color: 'black' },
      tickfont: { family: 'Arial, sans-serif',  size: 16, color: 'black' },
    },	
    yaxis: {
      title: 'undefined plot',
      titlefont: { family: 'Arial, sans-serif', size: 24, color: 'black' },
      tickfont: { family: 'Arial, sans-serif',  size: 20, color: 'black' },
      ticklen: 0.5,
    },
    bargap: 0,
    barmode: 'stack',
    annotations: [{
  	xref: 'paper',
  	yref: 'paper',
  	xanchor: 'left',
  	yanchor: 'bottom',
  	x: -0.12,
  	y: -0.17, 
  	font: {
  	  family: 'sans serif',
  	  size: 12,
  	  color: 'green',
  	},
  	text: timing_string,
  	showarrow: false,
      }],
  };

  // adjust x-axis labels
  if (graph == 'rate') {
    basic_layout['yaxis']['title'] = 'Transfered Rate [GB/sec]'
  }
  if (graph == 'volume') {
    basic_layout['yaxis']['title'] = 'Transfered Volume [GB]'
  }
  if (graph == 'cumulative') {
    basic_layout['yaxis']['title'] = 'Cumulative Transfered Volume [GB]'
  }

  var layout = $.extend( true, {}, basic_layout );
  Plotly.newPlot('activity', plot_data, layout);
}
