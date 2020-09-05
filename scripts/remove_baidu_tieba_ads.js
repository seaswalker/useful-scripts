// ==UserScript==
// @name         去掉百度贴吧广告
// @namespace    https://github.com/seaswalker
// @version      帖子的dom结构是ul#thread_list下的class为j_thread_list的是帖子，其它的都是广告
// @description  RT
// @author       skywalker
// @match        https://tieba.baidu.com/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    window.addEventListener('load', (event) => {
         var threadList = $("ul#thread_list")
         if (threadList.length != 1) {
             console.log("没有找到ul#thread_list.")
             return
         }

        threadList.children("li").filter(":not(.j_thread_list,.thread_top_list_folder)").remove()
    });
})();
