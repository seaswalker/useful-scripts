// ==UserScript==
// @name         叮咚FM全屏
// @namespace    https://github.com/seaswalker
// @version      0.1
// @description  济南电台叮咚FM看直播时无法全屏，原因是div.vcp-bigplay元素默认的80%高度遮挡住了html的视频控制菜单，修改之
// @author       skywalker
// @match        http://www.dingdongfm.cn/web/wx/liveIndex*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // Your code here...
    var vcp_bigplay = $("div.vcp-bigplay");
    if (vcp_bigplay.length != 1) {
        return;
    }
    vcp_bigplay[0].style.height = "50%";
})();
