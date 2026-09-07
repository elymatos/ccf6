@extends('workbench.layout')
@section('title', 'Runs — CCF6')
@section('subtitle', 'Experiment runs')

@section('content')
<section>
    <h2>Runs</h2>
    @if ($runs->isEmpty())
        <div class="panel muted">
            No artifacts yet. Run one:
            <code>PYTHONPATH=ccf6-runtime/src python3 -m ccf6 experiments/001-colour-selectivity-baseline.json artifacts</code>
        </div>
    @else
        <div class="panel">
            <table>
                <thead>
                <tr><th>#</th><th>Experiment</th><th>Kind</th><th>Started</th><th>Seconds</th><th>Stimuli</th><th>Digest</th></tr>
                </thead>
                <tbody>
                @foreach ($runs as $run)
                    <tr>
                        <td><code><strong>{{ $run['number'] ?? '—' }}</strong></code></td>
                        <td><a href="{{ route('runs.show', $run['run']) }}">{{ $run['name'] }}</a></td>
                        <td class="muted">{{ $run['kind'] }}</td>
                        <td class="muted">{{ \Illuminate\Support\Str::of($run['started'])->substr(0, 19)->replace('T', ' ') }}</td>
                        <td>{{ number_format($run['seconds'], 1) }}</td>
                        <td>{{ ($run['stimuli']['positions'] ?? 0) * count($run['stimuli']['colours'] ?? []) }}</td>
                        <td><code class="muted">{{ $run['digest'] }}</code></td>
                    </tr>
                @endforeach
                </tbody>
            </table>
        </div>
    @endif
</section>
@endsection
