import Link from "next/link";
import Image from "next/image";

export default function Home() {
  return (
    <div className="min-h-screen">
      {/* Navigation */}
      <nav className="border-b bg-white">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="text-xl font-bold text-blue-600">
            Obligation Extractor
          </div>
          <div className="flex items-center space-x-4">
            <Link href="/" className="text-blue-600 font-medium">
              Home
            </Link>
            <Link href="/upload" className="text-gray-600 hover:text-gray-900">
              Upload
            </Link>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="font-sans grid grid-rows-[20px_1fr_20px] items-center justify-items-center min-h-screen p-8 pb-20 gap-16 sm:p-20">
        <main className="flex flex-col gap-[32px] row-start-2 items-center sm:items-start">
          <div className="text-center sm:text-left">
            <h1 className="text-4xl font-bold mb-4">Obligation Extractor</h1>
            <p className="text-xl text-gray-600 mb-8">AI-powered legal document analysis</p>
          </div>

          <div className="flex gap-4 items-center flex-col sm:flex-row">
            <Link
              href="/upload"
              className="rounded-full border border-solid border-transparent transition-colors flex items-center justify-center bg-blue-600 text-white gap-2 hover:bg-blue-700 font-medium text-sm sm:text-base h-10 sm:h-12 px-4 sm:px-5 sm:w-auto"
            >
              📄 Upload Document
            </Link>
            <a
              className="rounded-full border border-solid border-black/[.08] dark:border-white/[.145] transition-colors flex items-center justify-center hover:bg-[#f2f2f2] dark:hover:bg-[#1a1a1a] hover:border-transparent font-medium text-sm sm:text-base h-10 sm:h-12 px-4 sm:px-5 w-full sm:w-auto md:w-[158px]"
              href="https://github.com/your-repo/obligation-extractor"
              target="_blank"
              rel="noopener noreferrer"
            >
              View on GitHub
            </a>
          </div>

          <div className="grid md:grid-cols-3 gap-6 mt-16">
            <div className="bg-white p-6 rounded-lg shadow-sm">
              <h3 className="text-lg font-semibold mb-2">📄 Document Support</h3>
              <p className="text-gray-600">Upload PDF and DOCX files or paste text directly</p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow-sm">
              <h3 className="text-lg font-semibold mb-2">🤖 AI-Powered</h3>
              <p className="text-gray-600">Advanced NLP to identify obligations and deadlines</p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow-sm">
              <h3 className="text-lg font-semibold mb-2">⚡ Fast Processing</h3>
              <p className="text-gray-600">Get results instantly with detailed analysis</p>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
