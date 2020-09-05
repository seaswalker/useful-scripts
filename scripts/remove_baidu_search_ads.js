// ==UserScript==
// @name 去除百度搜索结果中的广告
// @namespace https://github.com/seaswalker
// @version   0.1
// @description 原理: 百度搜索结果是由div#content_left下面的div组成，每个结果是一个div，有意义的结果div都包含c-container
//              class，所以直接移除就可以，但百度恶心在于使用JavaScript定时器判断是否广告div被移除，如果移除了会再重新加回来，
//              所以需要在document开始加载之前通过MutationObserver把所有scipt节点全部移除，这样百度的广告检查代码也就没有了，
//              对MutationObserver的添加必须在百度的代码被执行之前进行，因为百度通过script标签引入的js将MutationObserver
//              禁用了，太贱了，这个js的URL:
//              https://dss1.bdstatic.com/5eN1bjq8AAUYm2zgoY3K/r/www/cache/static/protocol/https/global/js/all_async_search_cbd25a7.js
//              相关代码:
//              try{window.MutationObserver=window.WebKitMutationObserver=window.MozMutationObserver=null}catch(e){}
//              这个问题是参考issue:
//              https://github.com/guyujiezi/cicada/issues/3
//              MutationObserver用法参考: 
//              https://medium.com/snips-ai/how-to-block-third-party-scripts-with-a-few-lines-of-javascript-f0b08b9c4c0
// @author skywalker
// @match https://www.baidu.com/s*
// @require http://libs.baidu.com/jquery/2.0.0/jquery.min.js
// @run-at document-start
// @grant none
// ==/UserScript==

(function () {
    'use strict';

    const observer = new window.MutationObserver(mutations => {
        mutations.forEach(({ addedNodes }) => {
            addedNodes.forEach(node => {
                if (node.nodeType == 1 && node.nodeName === "SCRIPT") {
                    node.parentElement.removeChild(node)
                }
            })
        })
    })

    observer.observe(document.documentElement, {
        subtree: true,
        childList: true
    })

    window.addEventListener('load', (event) => {
        var ads = $("div#content_left").children("div").filter(":not(.c-container)")
        console.log(`百度首页找到: ${ads.length}条广告`)

        ads.remove()
    });
})();
