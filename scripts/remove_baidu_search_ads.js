// ==UserScript==
// @name 去除百度搜索结果中的广告
// @namespace https://github.com/seaswalker
// @version   0.1
// @description 原理: 百度搜索结果是由div#content_left下面的div组成，每个结果是一个div，有意义的结果div都包含c-container
//              class，所以直接移除就可以，但百度恶心在于使用JavaScript定时器判断是否广告div被移除，如果移除了会再重新加回来，
//              所以需要在document开始加载之前通过MutationObserver把所有scipt节点全部移除，这样百度的广告检查代码也就没有了
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
