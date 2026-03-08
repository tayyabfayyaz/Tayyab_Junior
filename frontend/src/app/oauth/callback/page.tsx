"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

function CallbackContent() {
  const params = useSearchParams();
  const code = params.get("code");
  const error = params.get("error");
  const errorDescription = params.get("error_description");

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white rounded-lg shadow p-8 max-w-lg w-full">
          <h1 className="text-xl font-semibold text-red-600 mb-2">OAuth Error</h1>
          <p className="text-gray-700 font-mono text-sm">{error}</p>
          {errorDescription && (
            <p className="text-gray-500 text-sm mt-2">{errorDescription}</p>
          )}
        </div>
      </div>
    );
  }

  if (!code) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white rounded-lg shadow p-8 max-w-lg w-full">
          <h1 className="text-xl font-semibold text-gray-700 mb-2">No code received</h1>
          <p className="text-gray-500 text-sm">No authorization code was returned.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white rounded-lg shadow p-8 max-w-lg w-full">
        <h1 className="text-xl font-semibold text-green-600 mb-4">Authorization Successful</h1>
        <p className="text-gray-600 text-sm mb-3">
          Copy the authorization code below and run the setup script:
        </p>
        <div className="bg-gray-100 rounded p-3 break-all font-mono text-xs text-gray-800 mb-4">
          {code}
        </div>
        <p className="text-gray-500 text-xs">
          Run in your terminal:
        </p>
        <div className="bg-gray-900 text-green-400 rounded p-3 font-mono text-xs mt-2 break-all">
          python scripts/linkedin_oauth_setup.py --code &apos;{code}&apos;
        </div>
      </div>
    </div>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense>
      <CallbackContent />
    </Suspense>
  );
}
