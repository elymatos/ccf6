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

@if ($completion)
<section>
    <h2>Frozen cue completion</h2>
    <div class="panel">
        <p class="lede">
            Primary distance <code>{{ $completion['primary_distance'] }}</code> ·
            secondary diagnostic <code>{{ $completion['secondary_diagnostic'] }}</code> ·
            durable changes during evaluation {{ $summary['completion']['durable_changes_during_evaluation'] ?? 0 }}.
            Settling failures count as failures: {{ $summary['completion']['settling_failures'] ?? 0 }} recorded.
        </p>
        <table>
            <thead><tr><th class="l">Arm</th><th class="l">Condition</th><th>Correct basin</th></tr></thead>
            <tbody>
            @foreach (($summary['completion']['correct_basin_by_arm_and_condition'] ?? []) as $armId => $conditions)
                @foreach ($conditions as $condition => $correct)
                    <tr>
                        <td class="l"><code>{{ $armId }}</code></td>
                        <td class="l">{{ $condition }}</td>
                        <td>{{ $correct }}</td>
                    </tr>
                @endforeach
            @endforeach
            </tbody>
        </table>
    </div>

    @foreach ($completion['arms'] as $armId => $arm)
        <div class="panel" style="margin-top:16px">
            <h3><code>{{ $armId }}</code> · per-condition evidence</h3>
            @foreach ($arm['conditions'] as $condition => $rows)
                <details style="margin-bottom:10px">
                    <summary>{{ $condition }} Presentations</summary>
                    <table>
                        <thead><tr><th class="l">Presentation</th><th class="l">Category</th><th>Initial distance</th><th>Settled distance</th><th>Margin</th><th>Every competitor</th><th>Settling failure</th><th>Correct basin</th></tr></thead>
                        <tbody>
                        @foreach ($rows as $row)
                            <tr>
                                <td class="l"><code>{{ $row['id'] }}</code></td>
                                <td class="l"><code>{{ $row['category_id'] }}</code></td>
                                <td>{{ $row['initial_distance'] }}</td>
                                <td>{{ $row['settled_distance'] }}</td>
                                <td>{{ $row['margin'] }}</td>
                                <td>{{ $row['beats_every_competitor'] ? 'yes' : 'no' }}</td>
                                <td>{{ $row['settling_failure'] ? 'yes' : 'no' }}</td>
                                <td>{{ $row['correct_basin'] ? 'yes' : 'no' }}</td>
                            </tr>
                            <tr><td></td><td colspan="7" class="l muted">Standardized competitors <code>{{ json_encode($row['competing_distances']) }}</code> · cosine diagnostic <code>{{ json_encode(['correct' => $row['correct_cosine_distance'], 'competing' => $row['competing_cosine_distances']]) }}</code></td></tr>
                        @endforeach
                        </tbody>
                    </table>
                </details>
            @endforeach
        </div>
    @endforeach
</section>

<section>
    <h2>Ordered lexical reactivation</h2>
    @foreach ($completion['arms'] as $armId => $arm)
        <div class="panel" style="margin-bottom:16px">
            <h3><code>{{ $armId }}</code></h3>
            <table>
                <thead><tr><th class="l">Category</th><th class="l">Pseudoword</th><th>Correct distance</th><th class="l">Control distances</th><th>Settling failure</th><th>Correct beats all</th></tr></thead>
                <tbody>
                @foreach ($arm['lexical_reactivation'] as $row)
                    <tr>
                        <td class="l"><code>{{ $row['category_id'] }}</code></td>
                        <td class="l"><code>{{ $row['pseudoword_id'] }}</code></td>
                        <td>{{ $row['correct_distance'] }}</td>
                        <td class="l"><code>{{ json_encode($row['control_distances']) }}</code></td>
                        <td>{{ $row['settling_failure'] ? 'yes' : 'no' }}</td>
                        <td>{{ $row['correct_better_than_every_control'] ? 'yes' : 'no' }}</td>
                    </tr>
                @endforeach
                </tbody>
            </table>
        </div>
    @endforeach
</section>
@endif

@if ($webs)
<section>
    <h2>Causal Functional Web detection</h2>
    <div class="panel">
        @php($webSummary = $summary['web_detection'] ?? [])
        <p class="lede">
            {{ $webSummary['detected_webs'] ?? 0 }} detected webs ·
            {{ $webSummary['selected_memberships'] ?? 0 }} selected memberships ·
            {{ $webSummary['shared_columns'] ?? 0 }} shared Columns ·
            held-out used: {{ ($webs['held_out_used'] ?? true) ? 'yes' : 'no' }}.
        </p>
        @if (($webSummary['detected_webs'] ?? 0) === 0)
            <p><strong>No Functional Web detected.</strong> The negative result is retained rather than replaced by an activation-threshold set.</p>
        @endif
        <p class="muted">
            Reliability, Causal completion contribution, and Reciprocal effective connectivity must each exceed the
            {{ ($webs['detector']['control_quantile'] ?? 0) * 100 }}th-percentile control and pass FDR correction.
            Higher association activity distinguishable: {{ ($webSummary['association_distinguishable'] ?? false) ? 'yes' : 'no' }}.
        </p>
        <p>Shared membership <code>{{ json_encode($webs['shared_columns'] ?? []) }}</code></p>
        <p>Association distances <code>{{ json_encode($webs['association_distances'] ?? []) }}</code></p>
    </div>

    @foreach (($webs['webs'] ?? []) as $categoryId => $web)
        <div class="panel" style="margin-top:16px">
            <h3><code>{{ $categoryId }}</code> · {{ count($web['members']) }} members</h3>
            <p>Selected membership <code>{{ json_encode($web['members']) }}</code></p>
            @foreach ($web['columns'] as $label => $column)
                <details style="margin-bottom:10px">
                    <summary><code>{{ $label }}</code> · selected: {{ $column['selected'] ? 'yes' : 'no' }}</summary>
                    @foreach (['reliability' => 'Reliability', 'causal' => 'Causal completion contribution', 'connectivity' => 'Reciprocal effective connectivity'] as $key => $title)
                        @php($evidence = $column[$key])
                        <p>
                            <strong>{{ $title }}</strong> · score {{ $evidence['score'] }} ·
                            control threshold {{ $evidence['control_threshold'] }} ·
                            raw p {{ $evidence['raw_p_value'] }} · corrected p {{ $evidence['corrected_p_value'] }} ·
                            passed: {{ $evidence['passed'] ? 'yes' : 'no' }}
                        </p>
                        <details><summary>Control distribution</summary><code>{{ json_encode($evidence['control_distribution']) }}</code></details>
                    @endforeach
                </details>
            @endforeach
        </div>
    @endforeach
</section>
@endif
@endsection
