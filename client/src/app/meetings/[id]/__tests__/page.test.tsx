"use client";

import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createMemoryHistory } from 'history';
import { Router } from 'react-router-dom';
import { server } from '@/mocks/server';
import { rest } from 'msw';
import { MeetingPage } from '../page';
import { createApiClient } from '@/lib/api-client';
import { joinMeetingRoom, leaveMeetingRoom, getSocket } from '@/lib/socket';

// Mock Socket.IO
vi.mock('@/lib/socket', () => ({
  joinMeetingRoom: vi.fn(),
  leaveMeetingRoom: vi.fn(),
  getSocket: vi.fn(() => ({
    on: vi.fn(),
    emit: vi.fn(),
    disconnect: vi.fn(),
  })),
}));

// Mock API client
vi.mock('@/lib/api-client', () => ({
  createApiClient: vi.fn(),
}));

describe('MeetingPage', () => {
  const mockMeetingId = 'test-meeting-123';
  const mockUserId = 'test-user-456';
  const mockAccessToken = 'test-access-token';

  beforeEach(() => {
    // Setup test meeting data
    const mockMeeting = {
      id: mockMeetingId,
      title: 'Test Meeting',
      description: 'Test meeting description',
      start_time: '2023-01-01T12:00:00Z',
      end_time: null,
      status: 'scheduled',
      created_by: mockUserId,
      bot_status: 'not_started',
      language: 'en',
    };

    // Setup mock API responses
    server.use(
      rest.get(`/api/meetings/${mockMeetingId}`, (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json(mockMeeting)
        );
      }),

      rest.get(`/api/meetings/${mockMeetingId}/transcript`, (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json([])
        );
      }),

      rest.post(`/api/meetings/${mockMeetingId}/transcript`, (req, res, ctx) => {
        return res(
          ctx.status(201),
          ctx.json({ message: 'Transcript chunk added successfully' })
        );
      })
    );

    // Mock API client
    vi.mocked(createApiClient).mockReturnValue({
      meetings: {
        get: vi.fn().mockResolvedValue(mockMeeting),
        getTranscript: vi.fn().mockResolvedValue([]),
        addTranscriptChunk: vi.fn().mockResolvedValue({ message: 'Success' }),
      },
    });

    // Mock Socket.IO
    vi.mocked(joinMeetingRoom).mockResolvedValue(undefined);
    vi.mocked(leaveMeetingRoom).mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.clearAllMocks();
    server.resetHandlers();
  });

  describe('Initial Load', () => {
    it('should render loading state initially', async () => {
      const history = createMemoryHistory();
      history.push(`/meetings/${mockMeetingId}`);

      render(
        <Router history={history}>
          <MeetingPage />
        </Router>
      );

      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });

    it('should fetch meeting data on mount', async () => {
      const history = createMemoryHistory();
      history.push(`/meetings/${mockMeetingId}`);

      render(
        <Router history={history}>
          <MeetingPage />
        </Router>
      );

      await waitFor(() => {
        expect(screen.getByText('Test Meeting')).toBeInTheDocument();
        expect(screen.getByText('Test meeting description')).toBeInTheDocument();
      });

      expect(vi.mocked(createApiClient)).toHaveBeenCalledWith(mockAccessToken);
      expect(vi.mocked(createApiClient().meetings.get)).toHaveBeenCalledWith(mockMeetingId);
    });

    it('should handle meeting not found error', async () => {
      server.use(
        rest.get(`/api/meetings/${mockMeetingId}`, (req, res, ctx) => {
          return res(
            ctx.status(404),
            ctx.json({ message: 'Meeting not found' })
          );
        })
      );

      const history = createMemoryHistory();
      history.push(`/meetings/${mockMeetingId}`);

      render(
        <Router history={history}>
          <MeetingPage />
        </Router>
      );

      await waitFor(() => {
        expect(screen.getByText(/meeting not found/i)).toBeInTheDocument();
      });
    });

    it('should handle API errors gracefully', async () => {
      server.use(
        rest.get(`/api/meetings/${mockMeetingId}`, (req, res, ctx) => {
          return res(
            ctx.status(500),
            ctx.json({ message: 'Internal server error' })
          );
        })
      );

      const history = createMemoryHistory();
      history.push(`/meetings/${mockMeetingId}`);

      render(
        <Router history={history}>
          <MeetingPage />
        </Router>
      );

      await waitFor(() => {
        expect(screen.getByText(/internal server error/i)).toBeInTheDocument();
      });
    });
  });

  describe('Socket.IO Integration', () => {
    it('should join meeting room on mount', async () => {
      const history = createMemoryHistory();
      history.push(`/meetings/${mockMeetingId}`);

      render(
        <Router history={history}>
          <MeetingPage />
        </Router>
      );

      await waitFor(() => {
        expect(vi.mocked(joinMeetingRoom)).toHaveBeenCalledWith(mockMeetingId);
      });
    });

    it('should leave meeting room on unmount', () => {
      const history = createMemoryHistory();
      history.push(`/meetings/${mockMeetingId}`);

      const { unmount } = render(
        <Router history={history}>
          <MeetingPage />
        </Router>
      );

      unmount();

      expect(vi.mocked(leaveMeetingRoom)).toHaveBeenCalledWith(mockMeetingId);
    });

    it('should handle transcript chunk events', async () => {
      const history = createMemoryHistory();
      history.push(`/meetings/${mockMeetingId}`);

      render(
        <Router history={history}>
          <MeetingPage />
        </Router>
      );

      await waitFor(() => {
        // Simulate transcript chunk event
        const mockSocket = vi.mocked(getSocket).mock.results[0].value;
        mockSocket.on.mock.calls.forEach(([event, callback]) => {
          if (event === 'transcript_chunk') {
            callback({
              timestamp: 1,
              text: 'Test transcript chunk',
              speaker: 'Test Speaker',
              confidence: 0.95
            });
          }
        });

        expect(screen.getByText('Test transcript chunk')).toBeInTheDocument();
      });
    });

    it('should handle catch-up events', async () => {
      const history = createMemoryHistory();
      history.push(`/meetings/${mockMeetingId}`);

      render(
        <Router history={history}>
          <MeetingPage />
        </Router>
      );

      await waitFor(() => {
        // Simulate catch-up event
        const mockSocket = vi.mocked(getSocket).mock.results[0].value;
        mockSocket.on.mock.calls.forEach(([event, callback]) => {
          if (event === 'catch_up') {
            callback({
              meeting_id: mockMeetingId,
              chunks: [
                { timestamp: 1, text: 'Previous chunk 1' },
                { timestamp: 2, text: 'Previous chunk 2' }
              ],
              total_chunks: 2,
              buffer_size: 10,
              timestamp: new Date().toISOString()
            });
          }
        });

        expect(screen.getByText('Previous chunk 1')).toBeInTheDocument();
        expect(screen.getByText('Previous chunk 2')).toBeInTheDocument();
      });
    });

    it('should handle bot status events', async () => {
      const history = createMemoryHistory();
      history.push(`/meetings/${mockMeetingId}`);

      render(
        <Router history={history}>
          <MeetingPage />
        </Router>
      );

      await waitFor(() => {
        // Simulate bot status events
        const mockSocket = vi.mocked(getSocket).mock.results[0].value;
        
        // Test bot joining
        mockSocket.on.mock.calls.forEach(([event, callback]) => {
          if (event === 'bot_status') {
            callback({ status: 'joining', meeting_id: mockMeetingId });
          }
        });

        expect(screen.getByText(/joining/i)).toBeInTheDocument();

        // Test bot in progress
        mockSocket.on.mock.calls.forEach(([event, callback]) => {
          if (event === 'bot_status') {
            callback({ status: 'in_progress', meeting_id: mockMeetingId });
          }
        });

        expect(screen.getByText(/live/i)).toBeInTheDocument();

        // Test bot completed
        mockSocket.on.mock.calls.forEach(([event, callback]) => {
          if (event === 'bot_status') {
            callback({ status: 'completed', meeting_id: mockMeetingId });
          }
        });

        expect(screen.getByText(/completed/i)).toBeInTheDocument();
      });
    });
  });

  describe('User Interactions', () => {
    it('should handle user input for transcript', async () => {
      const history = createMemoryHistory();
      history.push(`/meetings/${mockMeetingId}`);

      render(
        <Router history={history}>
          <MeetingPage />
        </Router>
      );

      await waitFor(() => {
        // Find the input field and enter text
        const input = screen.getByPlaceholderText(/type a message/i);
        const sendButton = screen.getByRole('button', { name: /send/i });

        fireEvent.change(input, { target: { value: 'Test user message' } });
        fireEvent.click(sendButton);

        expect(vi.mocked(createApiClient().meetings.addTranscriptChunk)).toHaveBeenCalledWith(
          mockMeetingId,
          {
            timestamp: expect.any(Number),
            text: 'Test user message',
            speaker: 'user',
            confidence: 1.0
          }
        );
      });
    });

    it('should handle form submission via Enter key', async () => {
      const history = createMemoryHistory();
      history.push(`/meetings/${mockMeetingId}`);

      render(
        <Router history={history}>
          <MeetingPage />
        </Router>
      );

      await waitFor(() => {
        // Find the input field and enter text
        const input = screen.getByPlaceholderText(/type a message/i);

        fireEvent.change(input, { target: { value: 'Test message' } });
        fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

        expect(vi.mocked(createApiClient().meetings.addTranscriptChunk)).toHaveBeenCalled();
      });
    });

    it('should clear input after successful submission', async () => {
      const history = createMemoryHistory();
      history.push(`/meetings/${mockMeetingId}`);

      render(
        <Router history={history}>
          <MeetingPage />
        </Router>
      );

      await waitFor(() => {
        // Find the input field and enter text
        const input = screen.getByPlaceholderText(/type a message/i);
        const sendButton = screen.getByRole('button', { name: /send/i });

        fireEvent.change(input, { target: { value: 'Test message' } });
        fireEvent.click(sendButton);

        // Input should be cleared after submission
        expect(input).toHaveValue('');
      });
    });

    it('should handle empty input submission', async () => {
      const history = createMemoryHistory();
      history.push(`/meetings/${mockMeetingId}`);

      render(
        <Router history={history}>
          <MeetingPage />
        </Router>
      );

      await waitFor(() => {
        // Find the input field and try to submit empty message
        const input = screen.getByPlaceholderText(/type a message/i);
        const sendButton = screen.getByRole('button', { name: /send/i });

        fireEvent.change(input, { target: { value: '' } });
        fireEvent.click(sendButton);

        // API should not be called with empty message
        expect(vi.mocked(createApiClient().meetings.addTranscriptChunk)).not.toHaveBeenCalled();
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle transcript submission errors', async () => {
      server.use(
        rest.post(`/api/meetings/${mockMeetingId}/transcript`, (req, res, ctx) => {
          return res(
            ctx.status(500),
            ctx.json({ message: 'Failed to add transcript chunk' })
          );
        })
      );

      const history = createMemoryHistory();
      history.push(`/meetings/${mockMeetingId}`);

      render(
        <Router history={history}>
          <MeetingPage />
        </Router>
      );

      await waitFor(() => {
        // Find the input field and enter text
        const input = screen.getByPlaceholderText(/type a message/i);
        const sendButton = screen.getByRole('button', { name: /send/i });

        fireEvent.change(input, { target: { value: 'Test message' } });
        fireEvent.click(sendButton);

        // Should show error message
        expect(screen.getByText(/failed to add transcript chunk/i)).toBeInTheDocument();
      });
    });

    it('should handle network errors', async () => {
      server.use(
        rest.get(`/api/meetings/${mockMeetingId}`, (req, res, ctx) => {
          return res.networkError('Failed to fetch');
        })
      );

      const history = createMemoryHistory();
      history.push(`/meetings/${mockMeetingId}`);

      render(
        <Router history={history}>
          <MeetingPage />
        </Router>
      );

      await waitFor(() => {
        expect(screen.getByText(/network error/i)).toBeInTheDocument();
      });
    });

    it('should handle authentication errors', async () => {
      server.use(
        rest.get(`/api/meetings/${mockMeetingId}`, (req, res, ctx) => {
          return res(
            ctx.status(401),
            ctx.json({ message: 'Unauthorized' })
          );
        })
      );

      const history = createMemoryHistory();
      history.push(`/meetings/${mockMeetingId}`);

      render(
        <Router history={history}>
          <MeetingPage />
        </Router>
      );

      await waitFor(() => {
        expect(screen.getByText(/unauthorized/i)).toBeInTheDocument();
      });
    });
  });

  describe('Component Behavior', () => {
    it('should render meeting status correctly', async () => {
      const history = createMemoryHistory();
      history.push(`/meetings/${mockMeetingId}`);

      render(
        <Router history={history}>
          <MeetingPage />
        </Router>
      );

      await waitFor(() => {
        // Should show scheduled status initially
        expect(screen.getByText(/scheduled/i)).toBeInTheDocument();

        // Simulate bot joining
        const mockSocket = vi.mocked(getSocket).mock.results[0].value;
        mockSocket.on.mock.calls.forEach(([event, callback]) => {
          if (event === 'bot_status') {
            callback({ status: 'joining', meeting_id: mockMeetingId });
          }
        });

        expect(screen.getByText(/joining/i)).toBeInTheDocument();

        // Simulate bot in progress
        mockSocket.on.mock.calls.forEach(([event, callback]) => {
          if (event === 'bot_status') {
            callback({ status: 'in_progress', meeting_id: mockMeetingId });
          }
        });

        expect(screen.getByText(/live/i)).toBeInTheDocument();
      });
    });

    it('should render transcript chunks correctly', async () => {
      const history = createMemoryHistory();
      history.push(`/meetings/${mockMeetingId}`);

      render(
        <Router history={history}>
          <MeetingPage />
        </Router>
      );

      await waitFor(() => {
        // Simulate transcript chunks
        const mockSocket = vi.mocked(getSocket).mock.results[0].value;
        mockSocket.on.mock.calls.forEach(([event, callback]) => {
          if (event === 'transcript_chunk') {
            callback({
              timestamp: 1,
              text: 'First chunk',
              speaker: 'Speaker 1',
              confidence: 0.95
            });
            callback({
              timestamp: 2,
              text: 'Second chunk',
              speaker: 'Speaker 2',
              confidence: 0.92
            });
          }
        });

        expect(screen.getByText('First chunk')).toBeInTheDocument();
        expect(screen.getByText('Second chunk')).toBeInTheDocument();
      });
    });

    it('should handle real-time updates', async () => {
      const history = createMemoryHistory();
      history.push(`/meetings/${mockMeetingId}`);

      render(
        <Router history={history}>
          <MeetingPage />
        </Router>
      );

      await waitFor(() => {
        // Simulate real-time updates
        const mockSocket = vi.mocked(getSocket).mock.results[0].value;
        
        // Test multiple updates
        for (let i = 1; i <= 5; i++) {
          mockSocket.on.mock.calls.forEach(([event, callback]) => {
            if (event === 'transcript_chunk') {
              callback({
                timestamp: i,
                text: `Chunk ${i}`,
                speaker: `Speaker ${i % 2 + 1}`,
                confidence: 0.9 + (i * 0.01)
              });
            }
          });
        }

        // Verify all chunks are rendered
        for (let i = 1; i <= 5; i++) {
          expect(screen.getByText(`Chunk ${i}`)).toBeInTheDocument();
        }
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty transcript', async () => {
      server.use(
        rest.get(`/api/meetings/${mockMeetingId}/transcript`, (req, res, ctx) => {
          return res(
            ctx.status(200),
            ctx.json([])
          );
        })
      );

      const history = createMemoryHistory();
      history.push(`/meetings/${mockMeetingId}`);

      render(
        <Router history={history}>
          <MeetingPage />
        </Router>
      );

      await waitFor(() => {
        // Should show empty state
        expect(screen.getByText(/no transcript yet/i)).toBeInTheDocument();
      });
    });

    it('should handle very long transcript chunks', async () => {
      const history = createMemoryHistory();
      history.push(`/meetings/${mockMeetingId}`);

      render(
        <Router history={history}>
          <MeetingPage />
        </Router>
      );

      await waitFor(() => {
        // Simulate very long transcript chunk
        const mockSocket = vi.mocked(getSocket).mock.results[0].value;
        mockSocket.on.mock.calls.forEach(([event, callback]) => {
          if (event === 'transcript_chunk') {
            callback({
              timestamp: 1,
              text: 'A'.repeat(1000), // Very long text
              speaker: 'Speaker 1',
              confidence: 0.95
            });
          }
        });

        // Should handle long text without crashing
        expect(screen.getByText('A'.repeat(100))).toBeInTheDocument(); // Check partial text
      });
    });

    it('should handle special characters in transcript', async () => {
      const history = createMemoryHistory();
      history.push(`/meetings/${mockMeetingId}`);

      render(
        <Router history={history}>
          <MeetingPage />
        </Router>
      );

      await waitFor(() => {
        // Simulate transcript with special characters
        const mockSocket = vi.mocked(getSocket).mock.results[0].value;
        mockSocket.on.mock.calls.forEach(([event, callback]) => {
          if (event === 'transcript_chunk') {
            callback({
              timestamp: 1,
              text: 'Hello! @#$%^&*()_+{}|:\"<>,./?[]\\',
              speaker: 'Speaker 1',
              confidence: 0.95
            });
          }
        });

        expect(screen.getByText('Hello! @#$%^&*()_+{}|:\"<>,./?[]\\')).toBeInTheDocument();
      });
    });
  });
});