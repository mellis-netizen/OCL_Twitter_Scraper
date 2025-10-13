import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import apiClient from '../services/api';
import { feedSchema, FeedFormData } from '../utils/validation';
import { formatRelativeTime } from '../utils/helpers';
import type { Feed } from '../types/api';

export default function FeedManager() {
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingFeed, setEditingFeed] = useState<Feed | null>(null);
  const queryClient = useQueryClient();

  // Fetch feeds
  const { data: feeds = [], isLoading } = useQuery({
    queryKey: ['feeds'],
    queryFn: () => apiClient.getFeeds(),
  });

  // Create feed mutation
  const createMutation = useMutation({
    mutationFn: apiClient.createFeed.bind(apiClient),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feeds'] });
      setIsFormOpen(false);
      reset();
    },
  });

  // Update feed mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) =>
      apiClient.updateFeed(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feeds'] });
      setIsFormOpen(false);
      setEditingFeed(null);
      reset();
    },
  });

  // Delete feed mutation
  const deleteMutation = useMutation({
    mutationFn: apiClient.deleteFeed.bind(apiClient),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feeds'] });
    },
  });

  // Form handling
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FeedFormData>({
    resolver: zodResolver(feedSchema),
    defaultValues: editingFeed || {
      type: 'rss',
      priority: 3,
      is_active: true,
    },
  });

  const onSubmit = (data: FeedFormData) => {
    if (editingFeed) {
      updateMutation.mutate({ id: editingFeed.id, data });
    } else {
      createMutation.mutate(data);
    }
  };

  const handleEdit = (feed: Feed) => {
    setEditingFeed(feed);
    setIsFormOpen(true);
    reset(feed);
  };

  const handleDelete = (id: number) => {
    if (window.confirm('Are you sure you want to delete this feed?')) {
      deleteMutation.mutate(id);
    }
  };

  const handleCancel = () => {
    setIsFormOpen(false);
    setEditingFeed(null);
    reset();
  };

  const getSuccessRate = (feed: Feed) => {
    const total = feed.success_count + feed.failure_count;
    if (total === 0) return 0;
    return Math.round((feed.success_count / total) * 100);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-white">News Source Management</h2>
        <button
          onClick={() => setIsFormOpen(true)}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          + Add Feed
        </button>
      </div>

      {/* Form Modal */}
      {isFormOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-dark-800 rounded-lg p-6 max-w-2xl w-full">
            <h3 className="text-xl font-bold text-white mb-4">
              {editingFeed ? 'Edit Feed' : 'Add New Feed'}
            </h3>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Feed Name *
                </label>
                <input
                  {...register('name')}
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-white focus:ring-2 focus:ring-primary-500"
                  placeholder="e.g., The Block RSS"
                />
                {errors.name && (
                  <p className="text-red-500 text-sm mt-1">{errors.name.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Feed URL *
                </label>
                <input
                  {...register('url')}
                  type="url"
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-white focus:ring-2 focus:ring-primary-500"
                  placeholder="https://example.com/feed.xml"
                />
                {errors.url && (
                  <p className="text-red-500 text-sm mt-1">{errors.url.message}</p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Type
                  </label>
                  <select
                    {...register('type')}
                    className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-white focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="rss">RSS</option>
                    <option value="atom">Atom</option>
                    <option value="json">JSON Feed</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Priority (1-5)
                  </label>
                  <input
                    {...register('priority', { valueAsNumber: true })}
                    type="number"
                    min="1"
                    max="5"
                    className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-white focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>

              <div className="flex items-center">
                <input
                  {...register('is_active')}
                  type="checkbox"
                  className="w-4 h-4 text-primary-600 bg-dark-700 border-dark-600 rounded focus:ring-primary-500"
                />
                <label className="ml-2 text-sm text-gray-300">Active</label>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="submit"
                  disabled={createMutation.isPending || updateMutation.isPending}
                  className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
                >
                  {editingFeed ? 'Update' : 'Create'} Feed
                </button>
                <button
                  type="button"
                  onClick={handleCancel}
                  className="px-4 py-2 bg-dark-700 text-gray-300 rounded-lg hover:bg-dark-600 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Feeds List */}
      {isLoading ? (
        <div className="text-center py-8 text-gray-400">Loading feeds...</div>
      ) : feeds.length === 0 ? (
        <div className="text-center py-8 text-gray-400">
          No feeds configured. Add your first news source to start monitoring.
        </div>
      ) : (
        <div className="space-y-4">
          {feeds.map((feed) => (
            <div
              key={feed.id}
              className="bg-dark-800 rounded-lg p-4 border border-dark-700 hover:border-primary-500 transition-colors"
            >
              <div className="flex justify-between items-start mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-lg font-semibold text-white">{feed.name}</h3>
                    <span
                      className={`px-2 py-0.5 rounded text-xs ${
                        feed.is_active
                          ? 'bg-green-900 text-green-200'
                          : 'bg-gray-700 text-gray-400'
                      }`}
                    >
                      {feed.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <p className="text-sm text-gray-400 break-all">{feed.url}</p>
                </div>
                <span className="px-2 py-1 bg-dark-700 text-gray-300 rounded text-xs">
                  Priority: {feed.priority}
                </span>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3 text-sm">
                <div>
                  <div className="text-gray-400">Success Rate</div>
                  <div
                    className={`font-medium ${
                      getSuccessRate(feed) >= 80
                        ? 'text-green-400'
                        : getSuccessRate(feed) >= 50
                        ? 'text-yellow-400'
                        : 'text-red-400'
                    }`}
                  >
                    {getSuccessRate(feed)}%
                  </div>
                </div>
                <div>
                  <div className="text-gray-400">Articles Found</div>
                  <div className="font-medium text-white">{feed.articles_found}</div>
                </div>
                <div>
                  <div className="text-gray-400">TGE Alerts</div>
                  <div className="font-medium text-primary-400">{feed.tge_alerts_found}</div>
                </div>
                <div>
                  <div className="text-gray-400">Last Fetch</div>
                  <div className="text-white">{formatRelativeTime(feed.last_fetch)}</div>
                </div>
              </div>

              {feed.last_error && (
                <div className="mb-3 p-2 bg-red-900 bg-opacity-30 border border-red-800 rounded text-xs text-red-200">
                  Last Error: {feed.last_error}
                </div>
              )}

              <div className="flex gap-2">
                <button
                  onClick={() => handleEdit(feed)}
                  className="flex-1 px-3 py-1.5 bg-dark-700 text-gray-300 rounded hover:bg-dark-600 transition-colors text-sm"
                >
                  Edit
                </button>
                <button
                  onClick={() => handleDelete(feed.id)}
                  disabled={deleteMutation.isPending}
                  className="flex-1 px-3 py-1.5 bg-red-900 text-red-200 rounded hover:bg-red-800 transition-colors text-sm disabled:opacity-50"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
