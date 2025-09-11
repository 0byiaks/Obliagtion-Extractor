'use client'

import React, { useState } from 'react'
import Link from 'next/link'

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<any>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setResult(null)

    if (!file && text.trim() === '') {
      setError('Please select a file or enter some text.')
      return
    }

    const formData = new FormData()
    if (file) {
      formData.append('file', file)
    } else if (text.trim()) {
      formData.append('text', text.trim())
    }

    try {
      setLoading(true)
      const res = await fetch('http://127.0.0.1:8000/ingest', {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err?.detail || `Request failed with ${res.status}`)
      }

      const data = await res.json()
      setResult(data)
    } catch (err: any) {
      setError(err.message || 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen w-full">
      {/* Navigation */}
      <nav className="border-b bg-white">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link href="/" className="text-xl font-bold text-blue-600">
            Obligation Extractor
          </Link>
          <div className="flex items-center space-x-4">
            <Link href="/" className="text-gray-600 hover:text-gray-900">
              Home
            </Link>
            <Link href="/upload" className="text-blue-600 font-medium">
              Upload
            </Link>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="flex items-start justify-center p-6">
        <div className="w-full max-w-2xl space-y-6">
          <h1 className="text-2xl font-semibold">Upload contract or paste text</h1>
        <form onSubmit={handleSubmit} className="space-y-4 border rounded-xl p-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium">File (PDF/DOCX)</label>
            <input
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="block w-full cursor-pointer file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200"
            />
            <p className="text-xs text-gray-500">Choose a file OR paste text below (if both are provided, file wins).</p>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium">Or paste text</label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste contract text here..."
              className="w-full h-40 rounded-md border p-3 focus:outline-none focus:ring-2 focus:ring-gray-300"
            />
          </div>

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center justify-center rounded-md border px-4 py-2 text-sm font-medium hover:bg-gray-50 disabled:opacity-60"
            >
              {loading ? 'Submitting…' : 'Submit'}
            </button>
            <button
              type="button"
              onClick={() => { setFile(null); setText(''); setResult(null); setError(null) }}
              className="text-sm text-gray-600 hover:underline"
            >
              Reset
            </button>
          </div>

          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 p-3 text-red-700 text-sm">{error}</div>
          )}
        </form>

        {result && (
          <div className="space-y-4">
            <h2 className="text-lg font-medium">Processing Results</h2>
            
            {/* Document Info */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-blue-50 p-3 rounded-lg">
                <div className="text-sm text-blue-600 font-medium">Mode</div>
                <div className="text-lg font-semibold">{result.mode}</div>
              </div>
              <div className="bg-green-50 p-3 rounded-lg">
                <div className="text-sm text-green-600 font-medium">Sections</div>
                <div className="text-lg font-semibold">{result.sections}</div>
              </div>
              <div className="bg-purple-50 p-3 rounded-lg">
                <div className="text-sm text-purple-600 font-medium">Chunks</div>
                <div className="text-lg font-semibold">{result.clauses}</div>
              </div>
              <div className="bg-orange-50 p-3 rounded-lg">
                <div className="text-sm text-orange-600 font-medium">Characters</div>
                <div className="text-lg font-semibold">{result.char_count?.toLocaleString()}</div>
              </div>
            </div>

            {/* Preview */}
            {result.preview && (
              <div className="space-y-2">
                <h3 className="text-md font-medium">Document Preview</h3>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-sm text-gray-700">{result.preview}</p>
                </div>
              </div>
            )}

            {/* Chunks */}
            {result.chunks && result.chunks.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-md font-medium">Document Chunks ({result.chunks.length})</h3>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {result.chunks.map((chunk: string, index: number) => (
                    <div key={index} className="bg-gray-50 p-3 rounded-lg border">
                      <div className="text-xs text-gray-500 mb-1">Chunk {index + 1}</div>
                      <p className="text-sm text-gray-700">{chunk.substring(0, 200)}{chunk.length > 200 ? '...' : ''}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Raw Response */}
            <details className="space-y-2">
              <summary className="text-md font-medium cursor-pointer">Raw Response</summary>
              <div className="rounded-xl border p-4 bg-gray-50 overflow-auto">
                <pre className="text-sm whitespace-pre-wrap">{JSON.stringify(result, null, 2)}</pre>
              </div>
            </details>
          </div>
        )}
        </div>
      </div>
    </div>
  )
}