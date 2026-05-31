import { deleteModule, listModules, ModuleUploadError, uploadModule } from './modules';

describe('module lifecycle API', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('lists installed modules', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ modules: [] }), { status: 200 }));

    await expect(listModules()).resolves.toEqual({ modules: [] });

    expect(fetch).toHaveBeenCalledWith('/api/v1/modules', expect.objectContaining({ method: 'GET' }));
  });

  it('uploads module files as multipart form data', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ moduleId: 'test', displayName: 'Test' }), { status: 201 }),
    );

    await uploadModule(new File(['module'], 'test.py', { type: 'text/x-python' }));

    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/modules',
      expect.objectContaining({ method: 'POST', body: expect.any(FormData) }),
    );
  });

  it('returns structured validation errors for rejected uploads', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: {
            code: 'validation_failed',
            detail: 'Module validation failed',
            validationSummary: {
              overall_status: 'invalid',
              static_phase: { phase: 'static', status: 'failed', findings: [{ code: 'syntax', message: 'bad' }] },
              runtime_phase: { phase: 'runtime', status: 'skipped', findings: [] },
            },
          },
        }),
        { status: 400 },
      ),
    );

    await expect(uploadModule(new File(['bad'], 'bad.py'))).rejects.toMatchObject({
      code: 'validation_failed',
      validationSummary: expect.objectContaining({ overall_status: 'invalid' }),
    } satisfies Partial<ModuleUploadError>);
  });

  it('deletes modules by id', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 204 }));

    await deleteModule('test/module');

    expect(fetch).toHaveBeenCalledWith('/api/v1/modules/test%2Fmodule', expect.objectContaining({ method: 'DELETE' }));
  });
});
