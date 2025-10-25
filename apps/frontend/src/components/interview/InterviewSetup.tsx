'use client';

import React, { useState, FormEvent } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { ChatIcon } from '@/components/icons/ChatIcon';

interface InterviewSetupProps {
  onStart: (projectName: string) => void;
  isLoading: boolean;
}

export function InterviewSetup({ onStart, isLoading }: InterviewSetupProps) {
  const [projectName, setProjectName] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (projectName.trim()) {
      onStart(projectName.trim());
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <Card padding="lg">
        <div className="space-y-6">
          <div className="text-center space-y-4">
            <div className="flex justify-center">
              <div className="w-16 h-16 bg-benzol-green-100 rounded-full flex items-center justify-center">
                <ChatIcon className="w-8 h-8 text-benzol-green-500" />
              </div>
            </div>
            <h1 className="text-3xl font-bold text-deep-indigo-500">
              Start a New Interview
            </h1>
            <div className="space-y-3 text-left max-w-xl mx-auto">
              <p className="text-deep-indigo-400">
                Your AI Business Analyst will guide you through a structured interview to gather comprehensive requirements for your project.
              </p>
              <ul className="text-sm text-deep-indigo-400 space-y-2 list-disc list-inside">
                <li>Expect <strong>15-25 questions</strong> covering scope, users, constraints, and success criteria</li>
                <li>Each answer is processed in <strong>2-10 seconds</strong> as AI analyzes your response</li>
                <li><strong>Estimated time: 15-30 minutes</strong></li>
                <li>Provide as much or as little detail as you like - more detail helps generate better requirements</li>
              </ul>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="project-name"
                className="block text-sm font-medium text-deep-indigo-500 mb-2"
              >
                Project Name
              </label>
              <input
                id="project-name"
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="e.g., E-commerce Platform, Mobile App, API Service"
                className="
                  w-full px-4 py-3 rounded-lg border border-deep-indigo-200
                  bg-white text-deep-indigo-500
                  focus:outline-2 focus:outline-benzol-green-500
                  transition-colors duration-200
                  disabled:bg-deep-indigo-50 disabled:cursor-not-allowed
                "
                disabled={isLoading}
                required
              />
              <p className="mt-2 text-sm text-deep-indigo-400">
                Give your project a descriptive name to help us understand what you&apos;re building.
              </p>
            </div>

            <Button
              type="submit"
              disabled={!projectName.trim() || isLoading}
              className="w-full"
            >
              {isLoading ? 'Starting Interview...' : 'Start Interview'}
            </Button>
          </form>
        </div>
      </Card>
    </div>
  );
}
