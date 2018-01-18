var system = require('system');  
var page = require('webpage').create();

//如果是windows,设置编码为gbk，防止中文乱码,Linux本身是UTF-8
var osName = system.os.name;  
console.log('os name:' + osName);  
if ('windows' === osName.toLowerCase()) {  
    phantom.outputEncoding="gbk";
}

//获取第二个参数(即请求地址url).
var param = system.args[1];
var save_url = param.split("###")[0]
var save_func_name = param.split("###")[1]

//显示控制台日志.
page.onConsoleMessage = function(msg, lineNum, sourceId) {  
    console.log('CONSOLE: ' + msg + ' (from line #' + lineNum + ' in "' + sourceId + '")');
};

//打开给定url的页面.
var start = new Date().getTime();
page.open("http://127.0.0.1:8000/", function(status) {
    // console.log(url);
    if (status == 'success') {
        console.log('echarts页面加载完成,加载耗时:' + (new Date().getTime() - start) + ' ms');

        //由于echarts动画效果，延迟500毫秒确保图片渲染完毕再调用下载图片方法.
        setTimeout(function() {
            page.evaluate(function() {
                $("#username").val('admin')
                $("#password").val('123456')
                $("#submitbtn").click();
                // console.log(1111111111111);
                // postImage();
                // console.log("调用了echarts的下载图片功能.");
            });
        }, 500);
        setTimeout(function() {
            page.evaluate(function(temp_url) {
                location.href = temp_url
            },save_url);
        }, 3000)
        if (save_func_name == 'echartsTotalData') {
            setTimeout(function() {
                page.evaluate(function() {
                    postImage_total();
                });
            }, 5000)
        }
        else if(save_func_name == 'echartsTotalEfficiencyData') {
            setTimeout(function() {
                page.evaluate(function() {
                    postImage_total_efficiency();
                });
            }, 5000)
        }
        else if(save_func_name == 'echartsAvgScoreData') {
            setTimeout(function() {
                page.evaluate(function() {
                    postImage_avg_score();
                });
            }, 5000)
        }
        else if(save_func_name == 'echartsSuperAvgTotalData') {
            setTimeout(function() {
                page.evaluate(function() {
                    postImage_super_avg_total();
                });
            }, 5000)
        }
        
        setTimeout('exit_phantom()',10000)
    } else {
        console.log("页面加载失败 Page failed to load!");
    }

    // 3秒后再关闭浏览器.
    // setTimeout(function() {
    //     // console.log(page.title)
    //     phantom.exit();
    // }, 30000);
});
function exit_phantom(){
    // location.href = "http://127.0.0.1:8000/label_data/display_total_data/?flag=total&date_begin=&date_end=&time_delta=7"
    console.log(page.title)
    phantom.exit()
}
// a phantomjs example
// page.open("http://www.cnblogs.com/front-Thinking", function(status) {
//    if ( status === "success" ) {
//       console.log(page.title); 
//    } else {
//       console.log("Page failed to load."); 
//    }
//    phantom.exit(0);
// });