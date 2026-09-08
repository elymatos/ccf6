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

        $wiring = $this->json($dir.'/connectivity.json') ?? ['connectivity' => [], 'palette' => []];
        $connectivity = $wiring['connectivity'] ?? [];

        // An artifact written before the architecture was replaced records structures
        // this workbench has no page for. Migrating those runs is deliberately out of
        // scope — they are the record of a superseded design — so the page says what
        // the run is instead of failing to draw it.
        if (! array_key_exists('structures', $connectivity)) {
            return view('workbench.superseded', [
                'run' => basename($run),
                'manifest' => $this->manifest($dir),
                'summary' => $this->json($dir.'/summary.json') ?? [],
            ]);
        }

        return view('workbench.run', [
            'run' => basename($run),
            'manifest' => $this->manifest($dir),
            'definition' => $this->json($dir.'/definition.json') ?? [],
            'summary' => $this->json($dir.'/summary.json') ?? [],
            'snapshots' => $this->json($dir.'/snapshots.json') ?? [],
            'palette' => $wiring['palette'] ?? [],
            'structures' => $connectivity['structures'] ?? [],
            'spaces' => $connectivity['web']['spaces'] ?? [],
            'convergenceSources' => $connectivity['web']['convergence_sources'] ?? [],
            'schema' => $connectivity['schema'] ?? null,
            'index' => $connectivity['index'] ?? null,
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
}
