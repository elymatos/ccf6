@extends('workbench.layout')
@section('title', 'Experiment '.($manifest['number'] ?? '—').' — '.($manifest['name'] ?? 'Run'))
@section('subtitle', 'Experiment '.($manifest['number'] ?? '—').' · '.($manifest['name'] ?? $run))

@php
    $css = ['white' => '#ffffff', 'red' => '#d1453b', 'green' => '#2f9e44', 'blue' => '#2f5fd0',
            'yellow' => '#e5b100', 'cyan' => '#0ca5b0', 'magenta' => '#b5379b', 'black' => '#1c1c1a'];
    $palette = $wiring['palette'] ?: array_keys($css);
    $ok = ($summary['duplicate_pairs'] ?? 1) === 0 && ($summary['peak_is_a_bijection'] ?? false);
@endphp

@section('content')
<section>
    <h2>Experiment {{ $manifest['number'] ?? '—' }} — the question</h2>
    <div class="panel">
        <p class="lede" style="color:var(--ink)">{{ $definition['question'] ?? '—' }}</p>
        <p class="verdict {{ $ok ? 'yes' : 'no' }}">
            {{ $ok ? 'Yes — every position produces a different pattern.' : 'No — some positions are indistinguishable.' }}
        </p>
        <table style="max-width:620px">
            <tbody>
            <tr><td class="l">World positions presented</td><td>{{ $summary['positions'] }}</td></tr>
            <tr><td class="l">Distinct activation patterns</td><td>{{ $summary['distinct_patterns'] }}</td></tr>
            <tr><td class="l">Distinct peak Columns</td><td>{{ $summary['distinct_peaks'] }}</td></tr>
            <tr><td class="l">One peak Column per position (a bijection)</td>
                <td>{{ $summary['peak_is_a_bijection'] ? 'yes' : 'no' }}</td></tr>
            <tr><td class="l">Pairs of positions that look the same</td>
                <td>{{ $summary['duplicate_pairs'] }}</td></tr>
            <tr><td class="l">Positions that produced no activity</td>
                <td>{{ $summary['silent_positions'] }}</td></tr>
            <tr><td class="l">Most similar two positions (cosine)</td>
                <td>{{ number_format($summary['max_off_diagonal_similarity'], 4) }}</td></tr>
            <tr><td class="l">Average similarity between positions</td>
                <td>{{ number_format($summary['mean_off_diagonal_similarity'], 4) }}</td></tr>
            </tbody>
        </table>
        <p class="muted" style="margin:14px 0 0;max-width:70ch">
            Read the Level's output as a 64-element vector: one number per Column. Two positions
            are distinguishable exactly when their vectors differ. Cosine similarity compares
            direction and ignores magnitude, so two positions scoring 1.0 would be identical to
            everything downstream even if one fired harder than the other.
        </p>
    </div>
</section>

<section>
    <h2>Every position, side by side</h2>
    <div class="panel">
        <p class="lede">
            Left of each pair is the World with the colour placed at that position. Right is
            <code>position.L1</code>'s output, on the same 8×8 Grid. If the Level is a faithful code
            for position, the bright Column on the right tracks the coloured cell on the left, and
            no two right-hand pictures are alike.
        </p>
        <div class="tiles">
            @foreach ($positions['records'] as $index => $record)
                <figure class="tile">
                    <div class="pair">
                        <canvas class="world-mini" data-index="{{ $index }}" width="8" height="8"></canvas>
                        <canvas class="level-mini" data-index="{{ $index }}" width="8" height="8"></canvas>
                    </div>
                    <figcaption>({{ implode(',', $record['position']) }})</figcaption>
                </figure>
            @endforeach
        </div>
    </div>
</section>

<section>
    <h2>Every position against every other</h2>
    <div class="panel">
        <p class="lede">
            The similarity matrix. Each cell compares one position's pattern with another's: dark
            means alike, pale means different. The diagonal is a position compared with itself and
            is always 1. <strong>Any dark cell off the diagonal would be a duplicate</strong> — two
            places the Level cannot tell apart.
        </p>
        <div class="row" style="align-items:flex-start">
            <figure>
                <canvas id="similarity" width="64" height="64"
                        style="width:520px;height:520px"></canvas>
                <figcaption>64 × 64 positions, ordered row by row through the World</figcaption>
            </figure>
            <div style="flex:1;min-width:220px">
                @if (count($positions['duplicates']))
                    <table>
                        <thead><tr><th class="l">Position A</th><th class="l">Position B</th><th>Similarity</th></tr></thead>
                        <tbody>
                        @foreach ($positions['duplicates'] as $pair)
                            <tr><td class="l">({{ implode(',', $pair['a']) }})</td>
                                <td class="l">({{ implode(',', $pair['b']) }})</td>
                                <td>{{ number_format($pair['similarity'], 4) }}</td></tr>
                        @endforeach
                        </tbody>
                    </table>
                @else
                    <p class="muted" style="margin:0">
                        No duplicate pairs at a tolerance of
                        {{ $definition['duplicate_tolerance'] ?? '0.999' }}. The most similar two
                        positions score
                        {{ number_format($summary['max_off_diagonal_similarity'], 4) }}, which is
                        well below the threshold — they overlap because neighbouring Columns
                        inhibit one another, not because they are confusable.
                    </p>
                @endif
            </div>
        </div>
    </div>
</section>

<section>
    <h2>How this Level is wired</h2>
    <div class="panel">
        @foreach ($spaces as $space => $detail)
            @if ($detail['cortical_area'])
                <p class="muted" style="margin:0 0 10px">
                    <code>{{ $space }}</code> — {{ $detail['cortical_area'] }} cortex,
                    {{ $detail['modality'] ?? 'no modality of its own' }}
                </p>
            @endif
            <table>
                <thead>
                <tr><th class="l">Level</th><th>Columns</th><th class="l">Receives from</th>
                    <th class="l">How</th><th>Fan-in</th><th>Receptive field</th><th>Competes with</th></tr>
                </thead>
                <tbody>
                @foreach ($detail['levels'] as $row)
                    <tr>
                        <td class="l"><code>{{ $row['level'] }}</code></td>
                        <td>{{ $row['columns'] }}</td>
                        <td class="l muted">{{ $row['source'] }}</td>
                        <td class="l muted">{{ $row['rule'] }}</td>
                        <td>{{ $row['fan_in'] }}</td>
                        <td>{{ $row['receptive_field'] }}</td>
                        <td>{{ $row['competitors'] }}</td>
                    </tr>
                @endforeach
                </tbody>
            </table>
        @endforeach
    </div>
</section>

<style>
    .verdict { font-size: 17px; font-weight: 650; margin: 0 0 18px; padding: 12px 16px;
               border-radius: 8px; border: 1px solid var(--line); background: #fff; }
    .verdict.yes { border-color: #2f9e44; color: #1d6e30; }
    .verdict.no  { border-color: #d1453b; color: #96302a; }
    .tiles { display: grid; grid-template-columns: repeat(8, 1fr); gap: 14px 10px; }
    .tile { text-align: center; }
    .pair { display: flex; gap: 3px; justify-content: center; }
    .pair canvas { image-rendering: pixelated; width: 52px; height: 52px;
                   border: 1px solid var(--line); border-radius: 3px; }
    .tile figcaption { font-size: 10px; margin-top: 4px; }
</style>

<script>
const RECORDS = @json($positions['records']);
const SIMILARITY = @json($positions['similarity']);
const PALETTE_CSS = @json(array_map(fn ($name) => $css[$name] ?? '#ffffff', $palette));

function paint(canvas, rows, cols, colourOf) {
    const ctx = canvas.getContext('2d');
    const image = ctx.createImageData(cols, rows);
    for (let i = 0; i < rows; i++) {
        for (let j = 0; j < cols; j++) {
            const [r, g, b] = colourOf(i, j);
            const o = (i * cols + j) * 4;
            image.data[o] = r; image.data[o + 1] = g; image.data[o + 2] = b; image.data[o + 3] = 255;
        }
    }
    ctx.putImageData(image, 0, 0);
}

const hex = (value) => [
    parseInt(value.slice(1, 3), 16), parseInt(value.slice(3, 5), 16), parseInt(value.slice(5, 7), 16),
];
const heat = (t) => [
    Math.round(255 - Math.min(1, Math.max(0, t)) * 210),
    Math.round(255 - Math.min(1, Math.max(0, t)) * 190),
    Math.round(255 - Math.min(1, Math.max(0, t)) * 105),
];

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('canvas.world-mini').forEach((canvas) => {
        const record = RECORDS[+canvas.dataset.index];
        paint(canvas, record.world.length, record.world[0].length,
              (i, j) => hex(PALETTE_CSS[record.world[i][j]] || '#ffffff'));
    });

    document.querySelectorAll('canvas.level-mini').forEach((canvas) => {
        const record = RECORDS[+canvas.dataset.index];
        // Scaled to this position's own peak, so a faint pattern is still readable.
        const peak = Math.max(record.peak_value, 1e-6);
        paint(canvas, record.level.length, record.level[0].length,
              (i, j) => heat(record.level[i][j] / peak));
    });

    const matrix = document.getElementById('similarity');
    if (matrix) {
        paint(matrix, SIMILARITY.length, SIMILARITY.length,
              (i, j) => heat(SIMILARITY[i][j]));
    }
});
</script>
@endsection
