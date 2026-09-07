@extends('workbench.layout')
@section('title', 'Experiment '.($manifest['number'] ?? '—').' — '.($manifest['name'] ?? 'Run'))
@section('subtitle', 'Experiment '.($manifest['number'] ?? '—').' · '.($manifest['name'] ?? $run))

@php
    $css = ['white' => '#ffffff', 'red' => '#d1453b', 'green' => '#2f9e44', 'blue' => '#2f5fd0',
            'yellow' => '#e5b100', 'cyan' => '#0ca5b0', 'magenta' => '#b5379b', 'black' => '#1c1c1a'];
    $palette = $wiring['palette'] ?: array_keys($css);
@endphp

@section('content')
<section>
    <h2>Experiment {{ $manifest['number'] ?? '—' }} — what this run asked</h2>
    <div class="panel">
        <p class="lede" style="color:var(--ink)">{{ $definition['question'] ?? '—' }}</p>
        <p class="muted" style="margin:0">
            Every colour was shown at every one of the {{ $manifest['stimuli']['positions'] ?? 0 }}
            World positions, one at a time — {{ count($manifest['stimuli']['colours'] ?? []) * ($manifest['stimuli']['positions'] ?? 0) }}
            presentations in all. Nothing learned; the connections never changed.
            <a href="/docs/first-experiment">Read the plain-English explanation →</a>
        </p>
    </div>
</section>

<section>
    <h2>The World, and what the network saw</h2>
    <div class="panel">
        <p class="lede">
            The World is an {{ count($snapshots[0]['world'] ?? []) }}×{{ count($snapshots[0]['world'][0] ?? []) }}
            grid of coloured cells. Every cell has a colour and white is an ordinary colour, not an
            empty space. What reaches the network is not colour but <em>contrast</em>: how much a
            cell differs from its neighbours. A cell surrounded by eight unlike neighbours has
            contrast 1.0; a cell in a uniform region has contrast 0.
        </p>
        <div class="row">
            @foreach ($snapshots as $snapshot)
                <figure>
                    <div class="world" style="grid-template-columns:repeat({{ count($snapshot['world'][0]) }},26px)">
                        @foreach ($snapshot['world'] as $i => $row)
                            @foreach ($row as $j => $colour)
                                <i style="background:{{ $css[$palette[$colour]] ?? '#fff' }}"
                                   class="{{ [$i, $j] === $snapshot['position'] ? 'mark' : '' }}"></i>
                            @endforeach
                        @endforeach
                    </div>
                    <figcaption>
                        {{ $snapshot['colour'] }} at ({{ implode(',', $snapshot['position']) }})<br>
                        contrast {{ number_format($snapshot['contrast'], 3) }}
                    </figcaption>
                </figure>
            @endforeach
        </div>
        <p class="muted" style="margin:18px 0 0;max-width:68ch">
            The outlined cell is where the colour was placed. Note the corner presentations: a cell
            at a corner has only three neighbours inside the World, so its contrast is
            {{ number_format($snapshots[0]['contrast'] ?? 0, 3) }} rather than 1.0. That difference
            is real and it matters — it is finding 5 in the journal.
        </p>
    </div>
</section>

<section>
    <h2>What responded</h2>
    <div class="panel">
        <p class="lede">
            Each square is one Level, drawn as its Grid of Columns. Brightness is the Column's
            output. These are outputs only — the internal stages of a Column are not shown, because
            what matters here is what each Level passed on.
        </p>
        @foreach ($snapshots as $index => $snapshot)
            <div class="row" style="margin-bottom:22px;align-items:flex-start">
                <figure>
                    <div class="world" style="grid-template-columns:repeat({{ count($snapshot['world'][0]) }},26px)">
                        @foreach ($snapshot['world'] as $i => $row)
                            @foreach ($row as $j => $colour)
                                <i style="background:{{ $css[$palette[$colour]] ?? '#fff' }}"
                                   class="{{ [$i, $j] === $snapshot['position'] ? 'mark' : '' }}"></i>
                            @endforeach
                        @endforeach
                    </div>
                    <figcaption><strong>World</strong><br>{{ $snapshot['colour'] }} at ({{ implode(',', $snapshot['position']) }})</figcaption>
                </figure>
                @foreach ($snapshot['areas'] as $area => $levels)
                    @foreach ($levels as $level => $data)
                        <figure>
                            <canvas class="heat" data-snapshot="{{ $index }}" data-level="{{ $level }}"
                                    width="{{ $data['shape'][1] }}" height="{{ $data['shape'][0] }}"
                                    style="width:{{ max(52, $data['shape'][1] * 26) }}px;
                                           height:{{ max(26, $data['shape'][0] * 26) }}px"></canvas>
                            <figcaption>{{ $level }}</figcaption>
                        </figure>
                    @endforeach
                @endforeach
            </div>
        @endforeach
    </div>
</section>

<section>
    <h2>How the Levels are wired</h2>
    <div class="panel">
        <p class="lede">
            <strong>Fan-in</strong> is how many Columns send into one Column. <strong>Receptive
            field</strong> is how much of the World a Column can be influenced by. <strong>Competes
            with</strong> is how many Columns inhibit it. Every number below was written by the code
            that built the connections, so it cannot drift from what actually ran.
        </p>
        @foreach ($wiring['connectivity']['areas'] ?? [] as $area => $rows)
            <h3 style="font-size:14px;margin:20px 0 8px"><code>{{ $area }}</code></h3>
            <table>
                <thead>
                <tr><th class="l">Level</th><th>Columns</th><th class="l">Receives from</th>
                    <th class="l">How</th><th>Fan-in</th><th>Receptive field</th>
                    <th>Competes with</th><th class="l">Feedback from</th></tr>
                </thead>
                <tbody>
                @foreach ($rows as $row)
                    <tr>
                        <td class="l"><code>{{ $row['level'] }}</code></td>
                        <td>{{ $row['columns'] }}</td>
                        <td class="l muted">{{ $row['source'] }}</td>
                        <td class="l muted">{{ $row['rule'] }}</td>
                        <td>{{ $row['fan_in'] }}</td>
                        <td>{{ $row['receptive_field'] }}</td>
                        <td>{{ $row['competitors'] }}</td>
                        <td class="l muted">{{ $row['feedback_from'] ?? '—' }}</td>
                    </tr>
                @endforeach
                </tbody>
            </table>
        @endforeach
        <p class="muted" style="margin:18px 0 0;max-width:68ch">
            The Hub receives the top Level of both spokes:
            @foreach ($wiring['connectivity']['hub_sources'] ?? [] as $source)
                <code>{{ $source['level'] }}</code> ({{ $source['columns'] }} Columns){{ !$loop->last ? ' and ' : '' }}
            @endforeach
            — so of its {{ collect($wiring['connectivity']['hub_sources'] ?? [])->sum('columns') }}
            possible inputs, {{ $wiring['connectivity']['hub_sources'][0]['columns'] ?? 0 }} carry position.
        </p>
    </div>
</section>

<section>
    <h2>Selectivity by Level</h2>
    <div class="panel">
        <p class="lede">
            How much of each Level's response is explained by <em>which colour</em> was shown, and
            how much by <em>where</em> it was. A Level that answered "yellow, wherever it appears"
            would score high on colour. No learning ran, so these are the numbers arbitrary wiring
            gives — the null a learning rule has to beat.
        </p>
        <div id="selectivity" style="height:320px"></div>
        <table style="margin-top:16px">
            <thead>
            <tr><th class="l">Level</th><th>Columns</th><th>Colour max</th><th>Colour mean</th>
                <th>Position max</th><th>Position mean</th></tr>
            </thead>
            <tbody>
            @foreach ($summary as $level => $row)
                <tr>
                    <td class="l"><code>{{ $level }}</code></td>
                    <td class="muted">{{ $row['columns'] }}</td>
                    <td>{{ number_format($row['colour_selectivity_max'], 3) }}</td>
                    <td class="muted">{{ number_format($row['colour_selectivity_mean'], 3) }}</td>
                    <td>{{ number_format($row['position_selectivity_max'], 3) }}</td>
                    <td class="muted">{{ number_format($row['position_selectivity_mean'], 3) }}</td>
                </tr>
            @endforeach
            </tbody>
        </table>
    </div>
</section>

<script>
const SNAPSHOTS = @json($snapshots);
const SUMMARY = @json($summary);

// Light theme: pale is quiet, deep is active. Monotone in luminance, so it still
// reads in greyscale or in print.
function heat(v) {
    const t = Math.max(0, Math.min(1, v));
    return [
        Math.round(255 - t * 210),
        Math.round(255 - t * 190),
        Math.round(255 - t * 105),
    ];
}

function draw() {
    document.querySelectorAll('canvas.heat').forEach((canvas) => {
        const snapshot = SNAPSHOTS[+canvas.dataset.snapshot];
        const levelName = canvas.dataset.level;
        const data = snapshot.areas[levelName.split('.')[0]][levelName];
        const rows = data.shape[0], cols = data.shape[1];
        const ctx = canvas.getContext('2d');
        const image = ctx.createImageData(cols, rows);
        for (let i = 0; i < rows; i++) {
            for (let j = 0; j < cols; j++) {
                const [r, g, b] = heat(data.l5[i][j]);
                const o = (i * cols + j) * 4;
                image.data[o] = r; image.data[o + 1] = g; image.data[o + 2] = b; image.data[o + 3] = 255;
            }
        }
        ctx.putImageData(image, 0, 0);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    draw();
    const levels = Object.keys(SUMMARY);
    echarts.init(document.getElementById('selectivity'), null, { renderer: 'canvas' }).setOption({
        tooltip: { trigger: 'axis' },
        legend: { data: ['explained by colour', 'explained by position'], bottom: 0 },
        grid: { left: 60, right: 24, top: 24, bottom: 64 },
        xAxis: { type: 'category', data: levels, axisLabel: { rotate: 30 } },
        yAxis: { type: 'value', max: 1, name: 'variance explained' },
        series: [
            { name: 'explained by colour', type: 'bar',
              data: levels.map((l) => SUMMARY[l].colour_selectivity_max), itemStyle: { color: '#e5b100' } },
            { name: 'explained by position', type: 'bar',
              data: levels.map((l) => SUMMARY[l].position_selectivity_max), itemStyle: { color: '#2f5fd0' } },
        ],
    });
});
</script>
@endsection
