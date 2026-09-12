@extends('workbench.layout')
@section('title', ($manifest['name'] ?? 'Cortical circuit').' — CCF6')
@section('subtitle', $manifest['name'] ?? 'Cortical circuit')

@section('content')
@php
    $circuit = $summary['circuit'] ?? [];
    $processSummary = $summary['processes'] ?? [];
    $learningSummary = $summary['learning'] ?? [];
    $processes = $activity['processes'] ?? [];
@endphp

<section>
    <div class="panel">
        <p class="lede"><strong>Explicit laminar cortical circuit.</strong> {{ $manifest['question'] ?? '' }}</p>
        <p class="muted" style="margin:0">
            Run <code>{{ $run }}</code> · contract <code>{{ $manifest['contract'] ?? '—' }}</code> ·
            runtime <code>{{ $manifest['software_version'] ?? '—' }}</code> · seed <code>{{ $topology['seed'] ?? '—' }}</code>
        </p>
    </div>
</section>

<section>
    <h2>Actual runtime trajectories</h2>
    <div class="panel">
        <p class="lede">This diagram reads population activity and signed pathway flux recorded by Python at every tick. It does not animate a decorative approximation. Choose a process, route family, and tick to inspect the causal circuit.</p>
        <div class="cortical-controls">
            <label>Process
                <select id="cortical-process">
                    @foreach ($processes as $identifier => $process)
                        <option value="{{ $identifier }}">{{ $identifier }}</option>
                    @endforeach
                </select>
            </label>
            <label>Pathways
                <select id="cortical-route"><option value="active">all active routes</option></select>
            </label>
            <label class="tick-control">Tick <output id="cortical-tick-value">0</output>
                <input id="cortical-tick" type="range" min="0" value="0" step="1">
            </label>
            <button id="cortical-play" type="button">Play</button>
        </div>
        <div class="cortical-status" id="cortical-status"></div>
        <div class="cortical-stage">
            <svg id="cortical-circuit" viewBox="0 0 1600 980" role="img" aria-label="Recorded cortical circuit activity and pathway flux"></svg>
        </div>
        <div class="cortical-legend">
            <span><i style="background:#2f5fd0"></i>excitatory</span>
            <span><i style="background:#b8860b"></i>modulatory</span>
            <span><i style="background:#d14f62"></i>inhibitory</span>
            <span>Node size and saturation = recorded activity</span>
            <span>Line opacity and width = recorded absolute flux</span>
        </div>
    </div>
</section>

<section>
    <h2>Circuit inventory</h2>
    <div class="row">
        <div class="panel cortical-stat"><strong>{{ $circuit['columns'] ?? 0 }}</strong><span>laminar Columns</span></div>
        <div class="panel cortical-stat"><strong>{{ $circuit['populations'] ?? 0 }}</strong><span>named populations</span></div>
        <div class="panel cortical-stat"><strong>{{ $circuit['pathways'] ?? 0 }}</strong><span>directed pathways</span></div>
        <div class="panel cortical-stat"><strong>{{ $processSummary['total'] ?? 0 }}</strong><span>process trials</span></div>
        <div class="panel cortical-stat"><strong>{{ $processSummary['with_controls'] ?? 0 }}</strong><span>causal controls</span></div>
    </div>
    <div class="panel" style="margin-top:16px;overflow:auto">
        <table>
            <thead><tr><th class="l">Level</th><th class="l">Columns</th><th>Count</th></tr></thead>
            <tbody>
            @foreach (($topology['hierarchy'] ?? []) as $level => $columns)
                <tr><td class="l">{{ $level }}</td><td class="l"><code>{{ implode(', ', $columns) }}</code></td><td>{{ count($columns) }}</td></tr>
            @endforeach
            </tbody>
        </table>
    </div>
</section>

<section>
    <h2>Numerical process evidence</h2>
    <div class="panel" style="overflow:auto">
        <table>
            <thead><tr><th class="l">Process</th><th class="l">Routes</th><th>Ticks</th><th>Peak activity</th><th>Peak active populations</th><th>Final activity norm</th><th>Maximum control difference</th></tr></thead>
            <tbody>
            @foreach ($processes as $identifier => $process)
                @php($measurements = $process['measurements'] ?? [])
                <tr>
                    <td class="l"><code>{{ $identifier }}</code></td>
                    <td class="l">{{ implode(', ', $process['active_routes'] ?? []) }}</td>
                    <td>{{ $process['ticks'] ?? 0 }}</td>
                    <td>{{ number_format($measurements['peak_activity'] ?? 0, 6) }}</td>
                    <td>{{ $measurements['peak_active_populations'] ?? 0 }}</td>
                    <td>{{ number_format($measurements['final_activity_norm'] ?? 0, 6) }}</td>
                    <td>{{ isset($measurements['control_maximum_activity_difference']) ? number_format($measurements['control_maximum_activity_difference'], 6) : '—' }}</td>
                </tr>
            @endforeach
            </tbody>
        </table>
    </div>
</section>

<section>
    <h2>Hebbian pathway strengthening</h2>
    <div class="panel">
        <p class="lede"><strong>STDP postponed.</strong> Confirmed rate-coded co-activity changes three separately recorded physical factors. No spike-order rule is active.</p>
        <div class="row">
            <div class="cortical-learning"><strong>{{ $learningSummary['release_facilitation_changes'] ?? 0 }}</strong><span>Release facilitation changes</span></div>
            <div class="cortical-learning"><strong>{{ $learningSummary['postsynaptic_receptiveness_changes'] ?? 0 }}</strong><span>Postsynaptic receptiveness changes</span></div>
            <div class="cortical-learning"><strong>{{ $learningSummary['structural_growth_changes'] ?? 0 }}</strong><span>Structural growth changes</span></div>
        </div>
        @foreach ($processes as $identifier => $process)
            @if (! empty($process['learning']['changed_pathways']))
                <details style="margin-top:20px">
                    <summary><code>{{ $identifier }}</code> · {{ count($process['learning']['changed_pathways']) }} changed pathways</summary>
                    <div style="overflow:auto;margin-top:12px">
                        <table>
                            <thead><tr><th class="l">Pathway</th><th>Release before → after</th><th>Receptiveness before → after</th><th>Terminal boutons</th><th>Axonal branches</th><th>Dendritic spines</th><th>Effective strength</th></tr></thead>
                            <tbody>
                            @foreach ($process['learning']['changed_pathways'] as $pathway => $change)
                                <tr>
                                    <td class="l"><code>{{ $pathway }}</code></td>
                                    <td>{{ number_format($change['before']['release_facilitation'], 5) }} → {{ number_format($change['after']['release_facilitation'], 5) }}</td>
                                    <td>{{ number_format($change['before']['postsynaptic_receptiveness'], 5) }} → {{ number_format($change['after']['postsynaptic_receptiveness'], 5) }}</td>
                                    <td>{{ $change['before']['terminal_boutons'] }} → {{ $change['after']['terminal_boutons'] }}</td>
                                    <td>{{ $change['before']['axonal_branches'] }} → {{ $change['after']['axonal_branches'] }}</td>
                                    <td>{{ $change['before']['dendritic_spines'] }} → {{ $change['after']['dendritic_spines'] }}</td>
                                    <td>{{ number_format($change['before']['effective_strength'], 5) }} → {{ number_format($change['after']['effective_strength'], 5) }}</td>
                                </tr>
                            @endforeach
                            </tbody>
                        </table>
                    </div>
                </details>
            @endif
        @endforeach
    </div>
</section>

<section>
    <h2>All explicit pathways</h2>
    @foreach (collect($topology['pathways'] ?? [])->groupBy('route') as $route => $pathways)
        <details class="panel" style="margin-bottom:12px">
            <summary><strong>{{ $route }}</strong> · {{ $pathways->count() }} pathways</summary>
            <div style="overflow:auto;margin-top:12px">
                <table>
                    <thead><tr><th class="l">Pathway</th><th class="l">Source</th><th class="l">Target</th><th class="l">Effect</th><th>Declared</th><th>Seeded base</th><th class="l">Plastic</th></tr></thead>
                    <tbody>
                    @foreach ($pathways as $pathway)
                        <tr>
                            <td class="l"><code>{{ $pathway['id'] }}</code></td>
                            <td class="l"><code>{{ $pathway['source'] }}</code></td>
                            <td class="l"><code>{{ $pathway['target'] }}</code></td>
                            <td class="l">{{ $pathway['effect'] }}</td>
                            <td>{{ number_format($pathway['declared_strength'], 5) }}</td>
                            <td>{{ number_format($pathway['base_strength'], 5) }}</td>
                            <td class="l">{{ $pathway['plastic'] ? 'yes' : 'no' }}</td>
                        </tr>
                    @endforeach
                    </tbody>
                </table>
            </div>
        </details>
    @endforeach
</section>

<style>
    main { max-width: 1600px; width: 100%; }
    .cortical-controls { display:flex; flex-wrap:wrap; gap:12px; align-items:flex-end; margin-bottom:12px; }
    .cortical-controls label { display:grid; gap:4px; color:var(--dim); font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; }
    .cortical-controls select, .cortical-controls input, .cortical-controls button, #cortical-play { border:1px solid var(--line); border-radius:6px; background:#fff; color:var(--ink); padding:7px 9px; }
    .cortical-controls .tick-control { flex:1; min-width:240px; }
    .cortical-controls input { width:100%; padding:0; }
    .cortical-status { min-height:24px; color:var(--dim); font-family:ui-monospace,monospace; font-size:12px; }
    .cortical-stage { overflow:auto; border:1px solid var(--line); border-radius:8px; background:#fff; }
    #cortical-circuit { display:block; min-width:1050px; width:100%; height:auto; }
    .cortical-legend { display:flex; flex-wrap:wrap; gap:14px; margin-top:10px; color:var(--dim); font-size:11px; }
    .cortical-legend span { display:flex; align-items:center; gap:5px; }
    .cortical-legend i { width:18px; height:3px; border-radius:3px; }
    .cortical-stat { min-width:150px; display:grid; gap:2px; }
    .cortical-stat strong, .cortical-learning strong { font-size:24px; }
    .cortical-stat span, .cortical-learning span { color:var(--dim); font-size:12px; }
    .cortical-learning { display:grid; min-width:210px; }
    summary { cursor:pointer; }
</style>

<script>
(() => {
    const topology = {{ Illuminate\Support\Js::from($topology) }};
    const activity = {{ Illuminate\Support\Js::from($activity) }};
    const svg = document.getElementById('cortical-circuit');
    const processSelect = document.getElementById('cortical-process');
    const routeSelect = document.getElementById('cortical-route');
    const tickInput = document.getElementById('cortical-tick');
    const tickValue = document.getElementById('cortical-tick-value');
    const status = document.getElementById('cortical-status');
    const playButton = document.getElementById('cortical-play');
    const namespace = 'http://www.w3.org/2000/svg';
    const positions = new Map();
    const nodeElements = new Map();
    const pathwayElements = [];
    let timer = null;

    const localOffsets = {
        L23Tuft: [-44, -76], L5Tuft: [44, -76], VIP: [-72, -28],
        L23Pyr: [-18, -24], PV23: [20, -24], SOM23: [58, -24],
        L4Pyr: [-18, 18], PV4: [28, 18], L5Pyr: [-18, 58],
        PV5: [24, 58], SOM5: [60, 58], L6Pyr: [-18, 94],
    };
    const kindColors = {
        pyramidal: '#2f5fd0', tuft: '#b8860b', pv: '#d14f62',
        som: '#4f8e57', vip: '#c28a22', relay: '#52789f', state: '#8259a8',
    };
    const levelY = { higher: 120, middle: 440, lower: 760 };
    const effectColors = { excitatory: '#2f5fd0', modulatory: '#b8860b', inhibitory: '#d14f62' };

    const element = (name, attributes = {}) => {
        const created = document.createElementNS(namespace, name);
        Object.entries(attributes).forEach(([key, value]) => created.setAttribute(key, value));
        return created;
    };

    const addText = (x, y, value, attributes = {}) => {
        const text = element('text', { x, y, ...attributes });
        text.textContent = value;
        svg.appendChild(text);
        return text;
    };
    const definitions = element('defs');
    Object.entries(effectColors).forEach(([effect, color]) => {
        const marker = element('marker', {
            id: `cortical-${effect}`,
            viewBox: '0 0 10 10',
            refX: 9,
            refY: 5,
            markerWidth: 6,
            markerHeight: 6,
            orient: 'auto',
        });
        const shape = effect === 'inhibitory'
            ? element('path', { d: 'M8 1V9', stroke: color, 'stroke-width': 2.5 })
            : element('path', { d: 'M0 0L10 5L0 10Z', fill: color });
        marker.appendChild(shape);
        definitions.appendChild(marker);
    });
    svg.appendChild(definitions);

    Object.entries(topology.hierarchy || {}).forEach(([level, columns]) => {
        columns.forEach((column, index) => {
            const x = 110 + ((index + 1) * 1380 / (columns.length + 1));
            const y = levelY[level];
            const box = element('rect', { x: x - 92, y: y - 105, width: 184, height: 225, rx: 12, fill: '#fbfbfa', stroke: '#d8d8d3' });
            svg.appendChild(box);
            addText(x, y - 84, `${level.toUpperCase()} · ${column}`, { 'text-anchor': 'middle', fill: '#6b6b66', 'font-size': 12, 'font-weight': 700 });
            (topology.columns[column]?.populations || []).forEach(identifier => {
                const local = identifier.split('.')[1];
                const offset = localOffsets[local];
                if (offset) positions.set(identifier, [x + offset[0], y + offset[1]]);
            });
        });
    });
    const externalPositions = {
        thal: [80, 905], motor: [1520, 905], attention: [1170, 35],
        arousal: [1280, 35], novelty: [1390, 35], reward: [1500, 35],
    };
    Object.entries(externalPositions).forEach(([identifier, position]) => positions.set(identifier, position));

    (topology.pathways || []).forEach((pathway, index) => {
        const source = positions.get(pathway.source);
        const target = positions.get(pathway.target);
        if (!source || !target) return;
        const line = element('line', {
            x1: source[0], y1: source[1], x2: target[0], y2: target[1],
            stroke: effectColors[pathway.effect], 'stroke-width': 1, opacity: .03,
            'data-route': pathway.route,
            'marker-end': `url(#cortical-${pathway.effect})`,
        });
        const title = element('title');
        title.textContent = `${pathway.id} · ${pathway.effect} · ${pathway.route}`;
        line.appendChild(title);
        svg.appendChild(line);
        pathwayElements.push({ line, pathway, index });
    });

    Object.entries(topology.populations || {}).forEach(([identifier, population]) => {
        const position = positions.get(identifier);
        if (!position) return;
        const group = element('g');
        const circle = element('circle', { cx: position[0], cy: position[1], r: 5, fill: kindColors[population.kind] || '#777', opacity: .2, stroke: '#fff', 'stroke-width': 1.5 });
        const title = element('title');
        title.textContent = `${identifier} · ${population.kind} · ${population.layer || population.level}`;
        circle.appendChild(title);
        group.appendChild(circle);
        const label = element('text', { x: position[0], y: position[1] + 17, 'text-anchor': 'middle', fill: '#555', 'font-size': 8 });
        label.textContent = identifier.includes('.') ? identifier.split('.')[1] : identifier;
        group.appendChild(label);
        svg.appendChild(group);
        nodeElements.set(identifier, circle);
    });

    const updateRoutes = process => {
        routeSelect.replaceChildren(new Option('all active routes', 'active'));
        process.active_routes.forEach(route => routeSelect.add(new Option(route, route)));
    };

    const render = () => {
        const process = activity.processes[processSelect.value];
        if (!process) return;
        const tick = Number(tickInput.value);
        const values = process.trajectory[tick];
        const fluxes = process.pathway_flux_trajectory[tick];
        const labelIndex = new Map(activity.labels.map((label, index) => [label, index]));
        nodeElements.forEach((circle, identifier) => {
            const value = values[labelIndex.get(identifier)] || 0;
            circle.setAttribute('r', String(4 + value * 11));
            circle.setAttribute('opacity', String(.15 + value * .85));
        });
        const route = routeSelect.value;
        const activeRoutes = new Set(process.active_routes);
        pathwayElements.forEach(({ line, pathway, index }) => {
            const selected = activeRoutes.has(pathway.route) && (route === 'active' || route === pathway.route);
            const flux = Math.abs(fluxes[index] || 0);
            line.setAttribute('opacity', selected ? String(Math.min(.9, .025 + flux * 1.8)) : '0');
            line.setAttribute('stroke-width', String(Math.min(6, .7 + flux * 5)));
        });
        tickValue.value = tick;
        const measurement = process.measurements;
        status.textContent = `${processSelect.value} · tick ${tick}/${process.ticks} · peak ${Number(measurement.peak_activity).toFixed(5)} at ${measurement.peak_activity_population}`;
    };

    const selectProcess = () => {
        const process = activity.processes[processSelect.value];
        tickInput.max = process.ticks;
        tickInput.value = 0;
        updateRoutes(process);
        render();
    };
    processSelect.addEventListener('change', selectProcess);
    routeSelect.addEventListener('change', render);
    tickInput.addEventListener('input', render);
    playButton.addEventListener('click', () => {
        if (timer) {
            clearInterval(timer); timer = null; playButton.textContent = 'Play'; return;
        }
        playButton.textContent = 'Pause';
        timer = setInterval(() => {
            const maximum = Number(tickInput.max);
            tickInput.value = Number(tickInput.value) >= maximum ? 0 : Number(tickInput.value) + 1;
            render();
        }, 120);
    });
    selectProcess();
})();
</script>
@endsection
