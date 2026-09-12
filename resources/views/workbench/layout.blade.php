<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>@yield('title', 'CCF6 workbench')</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/echarts/5.5.1/echarts.min.js"></script>
    <style>
        :root {
            --bg: #ffffff; --panel: #fbfbfa; --line: #e2e2df;
            --ink: #1c1c1a; --dim: #6b6b66; --accent: #2f5fd0; --warm: #b8860b;
        }
        * { box-sizing: border-box; }
        body { margin: 0; background: var(--bg); color: var(--ink);
               font: 15px/1.6 ui-sans-serif, system-ui, -apple-system, sans-serif; }
        a { color: var(--accent); text-decoration: none; }
        a:hover { text-decoration: underline; }
        header { padding: 18px 28px; border-bottom: 1px solid var(--line);
                 display: flex; align-items: baseline; gap: 16px; }
        header h1 { font-size: 15px; margin: 0; letter-spacing: .07em; text-transform: uppercase; }
        header span { color: var(--dim); font-size: 14px; }
        header nav { margin-left: auto; }
        main { padding: 28px; max-width: 1180px; }
        section { margin-bottom: 40px; }
        h2 { font-size: 12px; text-transform: uppercase; letter-spacing: .1em;
             color: var(--dim); margin: 0 0 12px; font-weight: 700; }
        .panel { background: var(--panel); border: 1px solid var(--line);
                 border-radius: 10px; padding: 20px; }
        .lede { margin: 0 0 18px; color: var(--dim); max-width: 68ch; }
        table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }
        th, td { text-align: right; padding: 7px 10px; border-bottom: 1px solid var(--line); }
        th:first-child, td:first-child, th.l, td.l { text-align: left; }
        th { color: var(--dim); font-weight: 700; font-size: 11px;
             text-transform: uppercase; letter-spacing: .06em; }
        tbody tr:last-child td { border-bottom: none; }
        code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; }
        .muted { color: var(--dim); }
        canvas.heat { image-rendering: pixelated; border: 1px solid var(--line);
                      border-radius: 4px; display: block; background: #fff; }
        .row { display: flex; gap: 28px; flex-wrap: wrap; align-items: flex-start; }
        figure { margin: 0; }
        figcaption { font-size: 12px; color: var(--dim); margin-top: 7px;
                     font-family: ui-monospace, monospace; }
        .world { display: grid; gap: 1px; background: var(--line);
                 border: 1px solid var(--line); border-radius: 4px; overflow: hidden; }
        .world i { display: block; width: 26px; height: 26px; }
        .world i.mark { box-shadow: inset 0 0 0 3px #1c1c1a; }
    </style>
</head>
<body>
<header>
    <h1><a href="{{ route('runs.index') }}">CCF6</a></h1>
    <span>@yield('subtitle', 'Connectionist Cognitive Framework, version 6')</span>
    <nav><a href="{{ url('/guide.html') }}">Guide</a></nav>
</header>
<main>@yield('content')</main>
</body>
</html>
