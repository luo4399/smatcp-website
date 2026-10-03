/* ============================================================================
   表格列宽拖拽（col-resize）
   ----------------------------------------------------------------------------
   给每个表头的右边缘加一个可拖拽的手柄：拖动改列宽，双击恢复该列默认宽度，
   调整结果记在 localStorage，刷新后仍在。

   三个关键决定，改之前请先看：

   1) 必须 table-layout: fixed。
      auto 布局下给 th 写 width 只是「建议值」，浏览器仍会按内容重算 ——
      拖起来列宽会跳。所以初始化时先量一遍当前实测列宽、写成 px，
      再切成 fixed。这样「默认观感」和加这个功能之前完全一致，
      只是从自动分配变成了可手动调。

   2) 拖 A 列边界，只改 A 列自己的宽度，绝不动别的列。表格总宽 = 各列之和。
      ⚠️ 这里改过一次（2026-09-24 luo：「列的宽度基本固定吧，不要随意乱跳，
      我筛选之后根本不知道了」）。原来的做法是「从右侧相邻列借宽度」，
      理由听起来合理（表格总宽不变、不会留白），实际很糟：
        · 拖 Gene 列 +200px，右邻的 Region 会从 264px 被挤到 64px；
        · Region 是允许折行的列（white-space: normal），64px 下
          "Upstream;Promoter;Open chromatin" 变成竖排的
          "Upstr / eam;P / romot / er;Op / en; / chrom / atin"，
          行高从 50px 涨到 200px+，整张表就没法看了；
        · 更根本的是「拖一列、动两列」不符合任何表格的直觉 ——
          Excel / AG Grid / TanStack Table 全都是只改被拖的那一列。
      所以现在：拖谁只改谁，右边的列整体平移、宽度不变。

   3) 表格宽度写死成 `<各列之和>px`，**同时把 `min-width` 也钉成同一个值**。
      ⚠️ 也不能用 `max(<各列之和>px, 100%)`（原来就是）。原因：
      table-layout: fixed 下，如果表格的**实际宽度大于各列之和**，浏览器会把
      多出来的余量按比例摊给每一列 —— 于是「你拖出来的宽度」根本不是实际宽度，
      而且只要余量一变，22 列会同时变宽变窄，看起来就是「列宽乱跳」。
      两个会触发它的口子，现在都堵上了：
        · `max(..., 100%)`：容器比表格宽时（本表容器恒定 1376px，表格 2620px，
          暂时碰不到，但换个容器尺寸就会碰上）；
        · CSS 里 `table.data-table { min-width: 2180px }`：用户把各列拖窄到
          总和不足 2180px 时会被它顶住，多出来的宽度又摊给各列。
          所以 apply() 里连 inline `min-width` 一起写。
      代价：各列之和 < 容器宽时表格不会撑满，右侧留白。这是「固定宽度」应有的
      样子（你设多宽就是多宽），而且有下面的每列下限兜着，总宽不会小到离谱。

   4) 切 fixed 之后列宽就冻住了，所以要留意「量的时候只渲染了一部分数据」。
      首页搜索表有 107,852 行、每页只渲染 10 行，第 1 页量出来的 Gene 列是 75px，
      而全量里 90% 的 Gene 值要 15 个字符（约 135px）—— 切 fixed 后翻页就会
      溢出/省略号。这类表请用 minColWidths 传一组按全量数据算出来的宽度。

   5) 每列有自己的拖拽下限，不是所有列共用 minWidth。
      下限 = max(minWidth, 该列表头文字宽 + 28px 内边距)，并且不超过该列的
      默认宽度（保证下限一定拖得到）。
      为什么不能共用一个 44px：表头文字会被挤成两行甚至竖排，而列宽一旦
      比表头还窄，用户连「这是哪一列」都看不出来 —— 正是 luo 说的
      「我筛选之后根本不知道了」。按表头文字定下限是最自然的尺度：
      「至少放得下它自己的列名」。

   用法：
     initColResize(document.querySelector('table.data-table'), {
       storageKey: 'gtop.cols.search',   // 不传则不记忆
       minWidth: 44,                     // 拖拽下限（会被上面第 5 条的每列下限抬高）
       minColWidths: idealColWidths(),   // 可选：每列默认宽度至少这么宽
       onWidths: w => {}                 // 可选：每次列宽变化后回调（w 是各列宽度数组）
     });
   ========================================================================== */
(function () {
  const MIN = 48;        // 单列最小宽度（px）

  function readSaved(key) {
    if (!key) return null;
    try { return JSON.parse(localStorage.getItem(key) || 'null'); } catch (e) { return null; }
  }

  function writeSaved(key, widths) {
    if (!key) return;
    try { localStorage.setItem(key, JSON.stringify(widths)); } catch (e) { /* 隐私模式下写不了，忽略 */ }
  }

  window.initColResize = function (table, opts) {
    if (!table || table.dataset.colResize) return null;
    const o = opts || {};
    const min = o.minWidth || MIN;
    const headRow = table.tHead && table.tHead.rows[0];
    if (!headRow) return null;

    const ths = Array.prototype.slice.call(headRow.cells);
    const n = ths.length;
    if (!n) return null;

    // ---- 1) 量出当前布局下的实测列宽，作为「默认宽度」（双击恢复用这个）
    const base = ths.map(th => Math.round(th.getBoundingClientRect().width));

    // ---- 1b) 叠加调用方给的「每列最小宽度」
    //
    // 为什么需要它：上面量到的是「当前这一屏」的列宽。首页搜索表是 table-layout: auto
    // 量出来的，量的时候只渲染了第 1 页那 10 行 —— 于是列宽是按这 10 行定的。
    // 切到 fixed 之后列宽就冻住了，翻到别的页遇到更长的值只能溢出（或显示省略号）。
    // 实测第 3 页的 Gene 是 "ENSG00000123456"（15 字符），而第 1 页那 10 行只有 8 字符宽。
    //
    // 所以调用方可以用 minColWidths 传一组「按全量数据算出来的」宽度，
    // 这里取两者较大的那个当默认值。传了就生效，不传完全不影响老行为。
    //   index.html 传的是 idealColWidths() 的结果，见那边的注释。
    if (Array.isArray(o.minColWidths)) {
      o.minColWidths.forEach((w, i) => {
        if (i < n && typeof w === 'number' && w > base[i]) base[i] = Math.round(w);
      });
    }

    // ---- 1c) 每列的拖拽下限（见文件头第 5 条）
    //
    // 下限 = max(全局 minWidth, 该列表头文字宽 + 28px)，并且不超过该列默认宽度。
    // 最后那个 min() 很关键：默认宽度本身就是从表头量出来的，按理 ≥ 下限；
    // 但如果某列表头被 CSS 压得比文字还窄，不夹一下就会出现「默认宽度本身就违规、
    // 一初始化就被顶宽」的自相矛盾。
    //
    // 逐个累加 th 的子节点宽度，**把排序图标和筛选按钮算进去、把拖拽手柄排除掉**：
    //   · 不算图标/按钮的话，拖到下限时它们会被挤出去压到右邻列
    //     （实测带筛选按钮的列会溢出 20px）；
    //   · 算上手柄的话（绝对定位在 right:-3px），下限虚高。
    //
    // ⚠️ 元素节点必须用 getBoundingClientRect()，**不能**用 Range：
    //    Range.selectNodeContents(el) 只覆盖 el 的 DOM 内容，拿不到
    //    ① 元素自身的内边距（.th-filter 有 padding: 1px 5px，实测少 14px）
    //    ② ::before 伪元素（Font Awesome 图标就是靠它画的，实测直接返回 0）
    //    实测 Type 列表头：Range 只量到 33.97 + 0 + 3.19 + 10 = 47，
    //    而真实需要 33.97 + 10 + 3.19 + 24 = 71 —— 差了整整一个筛选按钮。
    //    文字节点没有盒子，只能继续用 Range。
    const floors = ths.map((th, i) => {
      const r = document.createRange();
      let w = 0;
      th.childNodes.forEach(node => {
        if (node.nodeType === 1) {
          if (node.classList.contains('col-resizer')) return;
          w += node.getBoundingClientRect().width;
        } else if (node.nodeType === 3 && node.textContent.trim()) {
          r.selectNodeContents(node);
          w += r.getBoundingClientRect().width;
        }
      });
      return Math.min(Math.max(min, Math.ceil(w) + 26), base[i]);   // 24 内边距 + 2 余量
    });

    // ---- 2) 叠加用户上次的调整
    const saved = readSaved(o.storageKey);
    const widths = base.slice();
    if (Array.isArray(saved) && saved.length === n) {
      saved.forEach((w, i) => {
        // 存的宽度也要夹进下限：早先版本允许把列拖得比表头还窄，
        // 那些值还躺在 localStorage 里，不夹的话刷新出来还是窄条。
        if (typeof w === 'number' && w >= min) widths[i] = Math.max(Math.round(w), floors[i]);
      });
    }

    table.classList.add('col-resizable');
    table.dataset.colResize = '1';

    const apply = () => {
      ths.forEach((th, i) => { th.style.width = widths[i] + 'px'; });
      // 表格宽 = 各列之和，min-width 一起钉死，见文件头第 3 条。
      // 不这么写的话，只要「表格实际宽度 > 各列之和」（max(...,100%) 或 CSS 里的
      // min-width 都会造成），浏览器就把余量按比例摊给每一列 —— 拖出来的宽度
      // 不是实际宽度，而且余量一变 22 列一起动。
      const total = widths.reduce((a, b) => a + b, 0);
      table.style.width = total + 'px';
      table.style.minWidth = total + 'px';
      // 通知调用方「列宽变了」。首页搜索表用它把「固定在右侧的最后两列」的
      // 右偏移跟着最后一列的宽度走（见 index.html 的 pinRightCols）。
      // 不传 onWidths 完全不影响老行为。
      if (typeof o.onWidths === 'function') o.onWidths(widths.slice());
    };
    apply();

    // ---- 3) 手柄
    ths.forEach((th, i) => {
      th.classList.add('th-resizable');
      const h = document.createElement('span');
      h.className = 'col-resizer';
      h.setAttribute('aria-hidden', 'true');
      h.title = '拖动调整列宽 · 双击恢复默认';
      h.addEventListener('mousedown', ev => start(ev, i));
      h.addEventListener('dblclick', ev => {
        ev.preventDefault();
        ev.stopPropagation();
        widths[i] = base[i];
        apply();
        writeSaved(o.storageKey, widths);
      });
      // 表头本身有 onclick（排序），别让手柄上的点击冒泡过去
      h.addEventListener('click', ev => ev.stopPropagation());
      th.appendChild(h);
    });

    let drag = null;

    function start(ev, i) {
      if (ev.button !== 0) return;
      ev.preventDefault();
      ev.stopPropagation();
      drag = {
        i,
        x0: ev.clientX,
        w0: widths[i],
        moved: false
      };
      document.body.classList.add('col-resizing');
      window.addEventListener('mousemove', move);
      window.addEventListener('mouseup', end);
    }

    function move(ev) {
      if (!drag) return;
      const d = ev.clientX - drag.x0;
      if (Math.abs(d) > 2) drag.moved = true;

      // 只改被拖的这一列。别的列一律不动 —— 右边的列整体平移、宽度不变。
      // （2026-09-24 之前的版本会「从右邻列借宽度」，见文件头第 2 条，
      //  那是把右邻列挤成竖排文字的元凶。）
      widths[drag.i] = Math.max(floors[drag.i], Math.round(drag.w0 + d));
      apply();
    }

    function end() {
      if (!drag) return;
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseup', end);
      document.body.classList.remove('col-resizing');
      if (drag.moved) writeSaved(o.storageKey, widths);
      drag = null;
    }

    return {
      // 恢复全部默认列宽（控制台里可手动调用）
      reset() {
        base.forEach((w, i) => { widths[i] = w; });
        apply();
        writeSaved(o.storageKey, widths);
      },
      widths: () => widths.slice()
    };
  };
})();
