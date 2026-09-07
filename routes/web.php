<?php

use App\Http\Controllers\WorkbenchController;
use Illuminate\Support\Facades\Route;

Route::get('/', [WorkbenchController::class, 'index'])->name('runs.index');
Route::get('/runs/{run}', [WorkbenchController::class, 'show'])->name('runs.show');
Route::get('/docs/{page}', [WorkbenchController::class, 'doc'])->name('docs.show');
