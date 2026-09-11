@extends('workbench.layout')
@section('title', ($manifest['name'] ?? 'Target Basins').' — CCF6')
@section('subtitle', $manifest['name'] ?? 'Target Basins')

@section('content')
@php
    $armSummary = $summary['arms'] ?? [];
    $basinSummary = $summary['basins'] ?? [];
    $heldOutSummary = $summary['held_out'] ?? [];
@endphp

<section>
    <div class="panel">
        <p class="lede">{{ $manifest['question'] ?? '' }}</p>
        <p class="muted" style="margin:0">
            Run <code>{{ $run }}</code> · {{ $armSummary['count'] ?? 0 }} matched arms ·
            initial conditions matched: {{ ($armSummary['matched_initial_conditions'] ?? false) ? 'yes' : 'no' }}
        </p>
    </div>
</section>

<section>
    <h2>Matched experimental arms</h2>
    <div class="panel">
        <table>
            <thead><tr><th class="l">Arm</th><th class="l">Pairings</th><th class="l">Control difference</th><th>Durable change</th><th class="l">Initial topology digest</th></tr></thead>
            <tbody>
            @foreach (($arms['arms'] ?? []) as $arm)
                <tr>
                    <td class="l"><code>{{ $arm['id'] }}</code></td>
                    <td class="l"><code>{{ json_encode($arm['category_pairings']) }}</code></td>
                    <td class="l">{{ implode(', ', $arm['control_difference']) ?: 'none' }}</td>
                    <td>{{ $arm['durable_change'] ? 'yes' : 'no' }}</td>
                    <td class="l"><code>{{ $arm['initial_topology_digest'] }}</code></td>
                </tr>
                <tr>
                    <td></td>
                    <td colspan="4" class="l muted">
                        dataset <code>{{ $arm['dataset_digest'] }}</code> · split <code>{{ $arm['split_digest'] }}</code> ·
                        parameters <code>{{ $arm['parameter_digest'] }}</code> · final durable state <code>{{ $arm['final_durable_digest'] }}</code>
                    </td>
                </tr>
            @endforeach
            </tbody>
        </table>
    </div>
</section>

<section>
    <h2>Frozen Target Basins</h2>
    <div class="panel">
        <p class="lede">
            {{ $basinSummary['estimation_instances_per_category'] ?? 0 }} basin-estimation instances per category ·
            minimum scale {{ $basinSummary['minimum_scale'] ?? 0 }} ·
            held-out used for fit: {{ ($basinSummary['held_out_used_for_fit'] ?? true) ? 'yes' : 'no' }}
        </p>
    </div>

    @foreach (($basins['arms'] ?? []) as $armId => $arm)
        @php($frozen = $arm['frozen'])
        <div class="panel" style="margin-top:16px">
            <h3><code>{{ $armId }}</code></h3>
            <p><strong>Pooled scale</strong> <code>{{ json_encode($frozen['pooled_scale']) }}</code></p>
            <p class="muted">Fit splits: {{ implode(', ', $frozen['fit_splits']) }} · minimum scale {{ $frozen['minimum_scale'] }}</p>
            @foreach ($frozen['categories'] as $categoryId => $basin)
                <details style="margin-bottom:10px">
                    <summary><code>{{ $categoryId }}</code> · {{ $basin['reliable_columns'] }} reliable Columns · Frozen margin {{ $basin['margin'] }}</summary>
                    <p>Estimation instances <code>{{ json_encode($basin['instance_ids']) }}</code></p>
                    <p>Centroid <code>{{ json_encode($basin['centroid']) }}</code></p>
                    <p>Column stability (standard deviation) <code>{{ json_encode($basin['column_standard_deviation']) }}</code></p>
                    <p>Reliable mask <code>{{ json_encode($basin['reliable_mask']) }}</code></p>
                    <p>Within-category distances <code>{{ json_encode($basin['within_distances']) }}</code></p>
                    <p>Between-category distances <code>{{ json_encode($basin['between_distances']) }}</code></p>
                    <p>Cosine diagnostics <code>{{ json_encode(['within' => $basin['within_cosine_distances'], 'between' => $basin['between_cosine_distances']]) }}</code></p>
                </details>
            @endforeach
        </div>
    @endforeach
</section>

<section>
    <h2>Held-out basin evaluations</h2>
    @foreach (($basins['arms'] ?? []) as $armId => $arm)
        <div class="panel" style="margin-bottom:16px">
            <h3><code>{{ $armId }}</code> · {{ $heldOutSummary['correct_basin_by_arm'][$armId] ?? 0 }} / {{ $heldOutSummary['total_by_arm'][$armId] ?? 0 }} correct</h3>
            <table>
                <thead><tr><th class="l">Instance</th><th class="l">Expected basin</th><th>Initial distance</th><th>Settled distance</th><th>Frozen margin</th><th>Every competitor</th><th>Correct basin</th></tr></thead>
                <tbody>
                @foreach ($arm['held_out_evaluations'] as $evaluation)
                    <tr>
                        <td class="l"><code>{{ $evaluation['visual_instance_id'] }}</code></td>
                        <td class="l"><code>{{ $evaluation['expected_category'] }}</code></td>
                        <td>{{ $evaluation['initial_distance'] }}</td>
                        <td>{{ $evaluation['settled_distance'] }}</td>
                        <td>{{ $evaluation['margin'] }}</td>
                        <td>{{ $evaluation['beats_every_competitor'] ? 'yes' : 'no' }}</td>
                        <td>{{ $evaluation['correct_basin'] ? 'yes' : 'no' }}</td>
                    </tr>
                    <tr><td></td><td colspan="6" class="l muted">Competing distances <code>{{ json_encode($evaluation['competing_distances']) }}</code></td></tr>
                @endforeach
                </tbody>
            </table>
        </div>
    @endforeach
</section>
@endsection
