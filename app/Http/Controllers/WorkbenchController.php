<?php

namespace App\Http\Controllers;

use Illuminate\Support\Facades\File;
use Illuminate\Support\Str;
use Illuminate\View\View;

/**
 * The workbench reads run artifacts. It does not own them and it does not compute
 * anything the runtime could have computed: every number on screen was written by
 * the Python runtime and is read back verbatim (ADR-0007).
 */
class WorkbenchController extends Controller
{
    private function root(): string
    {
        return rtrim(config('ccf6.artifact_root', base_path('artifacts')), '/');
    }

    /** Every run on disk, newest first. */
    public function index(): View
    {
        $runs = collect(File::directories($this->root()))
            ->map(fn ($dir) => $this->manifest($dir))
            ->filter()
            ->sortByDesc('started')
            ->values();

        return view('workbench.index', ['runs' => $runs]);
    }

    public function show(string $run): View
    {
        $dir = $this->root().'/'.basename($run);
        abort_unless(File::isDirectory($dir), 404);

        $manifest = $this->manifest($dir);
        $summary = $this->json($dir.'/summary.json') ?? [];

        if (($manifest['contract'] ?? null) === 'ncl-functional-web-v1') {
            if (($manifest['kind'] ?? null) === 'synthetic_lexical_grounding') {
                return view('workbench.domain', [
                    'run' => basename($run),
                    'manifest' => $manifest,
                    'summary' => $summary,
                    'dataset' => $this->json($dir.'/dataset.json') ?? [],
                ]);
            }

            if (($manifest['kind'] ?? null) === 'zero_rest_network') {
                return view('workbench.network', [
                    'run' => basename($run),
                    'manifest' => $manifest,
                    'summary' => $summary,
                    'topology' => $this->json($dir.'/topology.json') ?? [],
                    'activity' => $this->json($dir.'/activity.json') ?? [],
                ]);
            }

            if (($manifest['kind'] ?? null) === 'coordinated_presentation') {
                return view('workbench.presentation', [
                    'run' => basename($run),
                    'manifest' => $manifest,
                    'summary' => $summary,
                    'topology' => $this->json($dir.'/topology.json') ?? [],
                    'presentations' => $this->jsonLines($dir.'/presentations.jsonl'),
                ]);
            }
        }

        $wiring = $this->json($dir.'/connectivity.json') ?? ['connectivity' => [], 'palette' => []];
        $connectivity = $wiring['connectivity'] ?? [];

        // Historical artifacts remain immutable. The current workbench recognizes its
        // explicit contract and reports every older shape as superseded.
        if (($connectivity['model'] ?? null) !== 'ncl-column-network-v1') {
            return view('workbench.superseded', [
                'run' => basename($run),
                'manifest' => $manifest,
                'summary' => $summary,
            ]);
        }

        return view('workbench.run', [
            'run' => basename($run),
            'manifest' => $manifest,
            'definition' => $this->json($dir.'/definition.json') ?? [],
            'summary' => $summary,
            'snapshots' => $this->json($dir.'/snapshots.json') ?? [],
            'palette' => $wiring['palette'] ?? [],
            'populations' => $connectivity['populations'] ?? [],
        ]);
    }

    /** A document from docs/, rendered. The file on disk stays the source of truth. */
    public function doc(string $page): View
    {
        $path = base_path('docs/'.basename($page).'.md');
        abort_unless(File::exists($path), 404);

        return view('workbench.doc', [
            'title' => Str::of(File::get($path))->before("\n")->ltrim('# ')->toString(),
            'body' => Str::markdown(File::get($path)),
        ]);
    }

    private function manifest(string $dir): ?array
    {
        $manifest = $this->json($dir.'/manifest.json');

        return $manifest ? $manifest + ['run' => basename($dir)] : null;
    }

    private function json(string $path): ?array
    {
        return File::exists($path) ? json_decode(File::get($path), true) : null;
    }

    /** @return list<array<string, mixed>> */
    private function jsonLines(string $path): array
    {
        if (! File::exists($path)) {
            return [];
        }

        return array_values(array_map(
            fn (string $line): array => json_decode($line, true),
            array_filter(explode("\n", File::get($path))),
        ));
    }
}
