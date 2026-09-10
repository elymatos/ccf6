@extends('workbench.layout')
@section('title', ($manifest['name'] ?? 'Synthetic domain').' — CCF6')
@section('subtitle', $manifest['name'] ?? 'Synthetic domain')

@section('content')
@php($domain = $summary['domain'] ?? [])

<section>
    <div class="panel">
        <p class="lede">{{ $manifest['question'] ?? '' }}</p>
        <p class="muted" style="margin:0">
            Run <code>{{ $run }}</code> · seed <code>{{ $dataset['seed'] ?? '—' }}</code> ·
            contract <code>{{ $manifest['contract'] ?? '—' }}</code>
        </p>
    </div>
</section>

<section>
    <h2>Generated domain</h2>
    <div class="panel">
        <table>
            <thead><tr><th class="l">Measure</th><th>Recorded value</th></tr></thead>
            <tbody>
            <tr><td class="l">Categories</td><td>{{ $domain['categories'] ?? 0 }}</td></tr>
            <tr><td class="l">Visual property dimensions</td><td>{{ $domain['visual_property_dimensions'] ?? 0 }}</td></tr>
            <tr><td class="l">Acquisition instances per category</td><td>{{ $domain['instances_per_category']['acquisition'] ?? 0 }}</td></tr>
            <tr><td class="l">Basin-estimation instances per category</td><td>{{ $domain['instances_per_category']['basin_estimation'] ?? 0 }}</td></tr>
            <tr><td class="l">Final held-out instances per category</td><td>{{ $domain['instances_per_category']['final_held_out'] ?? 0 }}</td></tr>
            <tr><td class="l">Pseudowords</td><td>{{ $domain['pseudowords'] ?? 0 }}</td></tr>
            <tr><td class="l">Pairings</td><td>{{ $domain['pairings']['total'] ?? 0 }} pairings</td></tr>
            </tbody>
        </table>
    </div>
</section>

<section>
    <h2>Visual property dimensions</h2>
    <div class="panel">
        <table>
            <thead><tr><th class="l">Dimension</th><th class="l">Declared values</th></tr></thead>
            <tbody>
            @foreach (($dataset['visual_property_dimensions'] ?? []) as $dimension)
                <tr>
                    <td class="l"><code>{{ $dimension['id'] }}</code></td>
                    <td class="l">{{ implode(', ', $dimension['values']) }}</td>
                </tr>
            @endforeach
            </tbody>
        </table>
    </div>
</section>

<section>
    <h2>Categories and immutable splits</h2>
    @foreach (($dataset['categories'] ?? []) as $category)
        <div class="panel" style="margin-bottom:16px">
            <h3><code>{{ $category['id'] }}</code> ↔ <code>{{ $category['pseudoword_id'] }}</code></h3>
            <p class="muted">
                Prototype:
                @foreach ($category['prototype']['properties'] as $property)
                    <code>{{ $property['dimension'] }}={{ $property['value'] }}</code>{{ $loop->last ? '' : ' ·' }}
                @endforeach
            </p>
            <table>
                <thead><tr><th class="l">Split</th><th class="l">Instance</th><th class="l">Properties</th><th>Prototype distance</th></tr></thead>
                <tbody>
                @foreach ($category['splits'] as $split => $instances)
                    @foreach ($instances as $instance)
                        <tr>
                            <td class="l"><code>{{ $split }}</code></td>
                            <td class="l"><code>{{ $instance['id'] }}</code></td>
                            <td class="l">
                                @foreach ($instance['properties'] as $property)
                                    {{ $property['value'] }}{{ $loop->last ? '' : ' ·' }}
                                @endforeach
                            </td>
                            <td>{{ $instance['prototype_distance'] }}</td>
                        </tr>
                    @endforeach
                @endforeach
                </tbody>
            </table>
        </div>
    @endforeach
</section>

<section>
    <h2>Ordered pseudowords</h2>
    <div class="panel">
        <p class="muted">Auditory features: {{ implode(', ', $dataset['auditory_features'] ?? []) }}</p>
        <table>
            <thead><tr><th class="l">Segment</th><th class="l">Distributed features</th></tr></thead>
            <tbody>
            @foreach (($dataset['auditory_segments'] ?? []) as $segment)
                <tr><td class="l"><code>{{ $segment['id'] }}</code></td><td class="l">{{ implode(', ', $segment['features']) }}</td></tr>
            @endforeach
            </tbody>
        </table>
        <table style="margin-top:20px">
            <thead><tr><th class="l">Pseudoword</th><th class="l">Ordered segments</th><th class="l">Reversed</th><th class="l">Permuted</th><th class="l">Repeated</th></tr></thead>
            <tbody>
            @foreach (($dataset['pseudowords'] ?? []) as $pseudoword)
                <tr>
                    <td class="l"><code>{{ $pseudoword['id'] }}</code></td>
                    <td class="l">{{ implode(' → ', $pseudoword['segments']) }}</td>
                    <td class="l">{{ implode(' → ', $pseudoword['controls']['reversed']) }}</td>
                    <td class="l">{{ implode(' → ', $pseudoword['controls']['permuted']) }}</td>
                    <td class="l">{{ implode(' → ', $pseudoword['controls']['repeated_segment']) }}</td>
                </tr>
            @endforeach
            </tbody>
        </table>
    </div>
</section>

<section>
    <h2>Balanced acquisition pairings</h2>
    <div class="panel">
        <p class="lede">
            {{ $domain['pairings']['correct'] ?? 0 }} correct and
            {{ $domain['pairings']['mismatched'] ?? 0 }} mismatched Presentations.
        </p>
        <table>
            <thead><tr><th class="l">Pairing</th><th>Epoch</th><th class="l">Category</th><th class="l">Visual instance</th><th class="l">Pseudoword</th><th class="l">Kind</th><th>Success Signal</th></tr></thead>
            <tbody>
            @foreach (($dataset['pairings'] ?? []) as $pairing)
                <tr>
                    <td class="l"><code>{{ $pairing['id'] }}</code></td>
                    <td>{{ $pairing['epoch'] }}</td>
                    <td class="l"><code>{{ $pairing['category_id'] }}</code></td>
                    <td class="l"><code>{{ $pairing['visual_instance_id'] }}</code></td>
                    <td class="l"><code>{{ $pairing['pseudoword_id'] }}</code></td>
                    <td class="l">{{ $pairing['kind'] }}</td>
                    <td>{{ number_format($pairing['success_signal'], 1) }}</td>
                </tr>
            @endforeach
            </tbody>
        </table>
    </div>
</section>

<section>
    <h2>Constraint checks</h2>
    <div class="panel">
        <p class="lede">{{ $domain['constraints']['passed'] ?? 0 }} of {{ $domain['constraints']['total'] ?? 0 }} checks passed.</p>
        <table>
            <thead><tr><th class="l">Check</th><th>Status</th><th class="l">Recorded evidence</th></tr></thead>
            <tbody>
            @foreach (($dataset['constraint_checks'] ?? []) as $check)
                <tr>
                    <td class="l"><code>{{ $check['name'] }}</code></td>
                    <td>{{ $check['passed'] ? 'pass' : 'fail' }}</td>
                    <td class="l"><code>{{ json_encode($check['evidence']) }}</code></td>
                </tr>
            @endforeach
            </tbody>
        </table>
    </div>
</section>
@endsection
