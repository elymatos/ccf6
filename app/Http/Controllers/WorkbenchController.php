<?php

namespace App\Http\Controllers;

use Illuminate\Support\Facades\File;
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
        $wiring = $this->json($dir.'/connectivity.json') ?? ['connectivity' => [], 'palette' => []];
        $view = ($manifest['kind'] ?? '') === 'position_representation'
            ? 'workbench.position'
            : 'workbench.run';

        return view($view, [
            'positions' => $this->json($dir.'/positions.json') ?? ['records' => [], 'similarity' => [], 'duplicates' => []],
            'run' => basename($run),
            'manifest' => $manifest,
            'definition' => $this->json($dir.'/definition.json') ?? [],
            'summary' => $this->json($dir.'/summary.json') ?? [],
            'snapshots' => $this->snapshots($this->json($dir.'/snapshots.json') ?? []),
            'wiring' => $wiring,
            'spaces' => $this->spaces($wiring),
        ]);
    }

    /**
     * Every Space in a run, as name => [cortical_area, modality, levels].
     *
     * Runs written before "Area" was split into Space, Modality and Cortical Area
     * carry an `areas` key holding the Level rows directly, and say nothing about
     * siting. They are still readable, and what they never recorded is left null
     * rather than guessed at.
     */
    private function spaces(array $wiring): array
    {
        $connectivity = $wiring['connectivity'] ?? [];

        if (isset($connectivity['spaces'])) {
            return $connectivity['spaces'];
        }

        return collect($connectivity['areas'] ?? [])
            ->map(fn ($levels) => ['cortical_area' => null, 'modality' => null, 'levels' => $levels])
            ->all();
    }

    /** Snapshots, with the pre-split `areas` key read as `spaces`. */
    private function snapshots(array $snapshots): array
    {
        return array_map(function (array $snapshot) {
            $snapshot['spaces'] ??= $snapshot['areas'] ?? [];
            unset($snapshot['areas']);

            return $snapshot;
        }, $snapshots);
    }

    /** A document from docs/, rendered. The file on disk stays the source of truth. */
    public function doc(string $page): View
    {
        $path = base_path('docs/'.basename($page).'.md');
        abort_unless(File::exists($path), 404);

        return view('workbench.doc', [
            'title' => \Illuminate\Support\Str::of(File::get($path))->before("\n")->ltrim('# ')->toString(),
            'body' => \Illuminate\Support\Str::markdown(File::get($path)),
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
