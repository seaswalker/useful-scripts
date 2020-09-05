// ==UserScript==
// @name 去除百度搜索结果中的广告
// @namespace https://github.com/seaswalker
// @version   0.1
// @description 原理: 百度搜索结果是由div#content_left下面的div组成，每个结果是一个div，广告div都包含一个innerText为"广告"的span.
//              但百度恶心在于使用JavaScript定时器判断是否广告div被移除，如果移除了会再重新加回来，
//              所以需要在document开始加载之前通过MutationObserver监听节点添加事件，找到广告div并将其删除.
//              对MutationObserver的添加必须在百度的代码被执行之前进行，因为百度通过script标签引入的js将MutationObserver
//              禁用了，太贱了，这个js的URL:
//              https://dss1.bdstatic.com/5eN1bjq8AAUYm2zgoY3K/r/www/cache/static/protocol/https/global/js/all_async_search_cbd25a7.js
//              相关代码:
//              try{window.MutationObserver=window.WebKitMutationObserver=window.MozMutationObserver=null}catch(e){}
//              这个问题是参考issue:
//              https://github.com/guyujiezi/cicada/issues/3
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
            removeAds();
        })
    })

    observer.observe(document.documentElement, {
        subtree: true,
        childList: true
    })
})();

function removeAds() {
    $("div#content_left").children("div").filter(function() {
        return $(this).find("span:contains('广告')").length > 0
    }).remove();
}
