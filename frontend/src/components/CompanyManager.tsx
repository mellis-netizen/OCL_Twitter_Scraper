import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import apiClient from '../services/api';
import { companySchema, CompanyFormData } from '../utils/validation';
import { formatDate, getPriorityColor, parseArrayInput, formatArrayOutput } from '../utils/helpers';
import type { Company } from '../types/api';

export default function CompanyManager() {
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingCompany, setEditingCompany] = useState<Company | null>(null);
  const queryClient = useQueryClient();

  // Fetch companies
  const { data: companies = [], isLoading } = useQuery({
    queryKey: ['companies'],
    queryFn: () => apiClient.getCompanies(),
  });

  // Create company mutation
  const createMutation = useMutation({
    mutationFn: apiClient.createCompany.bind(apiClient),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      setIsFormOpen(false);
      reset();
    },
  });

  // Update company mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) =>
      apiClient.updateCompany(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      setIsFormOpen(false);
      setEditingCompany(null);
      reset();
    },
  });

  // Delete company mutation
  const deleteMutation = useMutation({
    mutationFn: apiClient.deleteCompany.bind(apiClient),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companies'] });
    },
  });

  // Form handling
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CompanyFormData>({
    resolver: zodResolver(companySchema),
    defaultValues: editingCompany || {
      priority: 'MEDIUM',
      status: 'active',
      aliases: [],
      tokens: [],
      exclusions: [],
    },
  });

  const onSubmit = (data: CompanyFormData) => {
    // Convert comma-separated strings to arrays
    const formattedData = {
      ...data,
      aliases: typeof data.aliases === 'string' ? parseArrayInput(data.aliases as any) : data.aliases,
      tokens: typeof data.tokens === 'string' ? parseArrayInput(data.tokens as any) : data.tokens,
      exclusions: typeof data.exclusions === 'string' ? parseArrayInput(data.exclusions as any) : data.exclusions,
    };

    if (editingCompany) {
      updateMutation.mutate({ id: editingCompany.id, data: formattedData });
    } else {
      createMutation.mutate(formattedData);
    }
  };

  const handleEdit = (company: Company) => {
    setEditingCompany(company);
    setIsFormOpen(true);
    reset({
      ...company,
      aliases: company.aliases as any,
      tokens: company.tokens as any,
      exclusions: company.exclusions as any,
    });
  };

  const handleDelete = (id: number) => {
    if (window.confirm('Are you sure you want to delete this company?')) {
      deleteMutation.mutate(id);
    }
  };

  const handleCancel = () => {
    setIsFormOpen(false);
    setEditingCompany(null);
    reset();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-white">Company Management</h2>
        <button
          onClick={() => setIsFormOpen(true)}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          + Add Company
        </button>
      </div>

      {/* Form Modal */}
      {isFormOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-dark-800 rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <h3 className="text-xl font-bold text-white mb-4">
              {editingCompany ? 'Edit Company' : 'Add New Company'}
            </h3>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Company Name *
                </label>
                <input
                  {...register('name')}
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-white focus:ring-2 focus:ring-primary-500"
                  placeholder="e.g., Caldera"
                />
                {errors.name && (
                  <p className="text-red-500 text-sm mt-1">{errors.name.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Aliases (comma-separated)
                </label>
                <input
                  {...register('aliases')}
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-white focus:ring-2 focus:ring-primary-500"
                  placeholder="e.g., Caldera Labs, Caldera Protocol"
                  defaultValue={editingCompany ? formatArrayOutput(editingCompany.aliases) : ''}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Token Symbols (comma-separated)
                </label>
                <input
                  {...register('tokens')}
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-white focus:ring-2 focus:ring-primary-500"
                  placeholder="e.g., CAL, CALDERA"
                  defaultValue={editingCompany ? formatArrayOutput(editingCompany.tokens) : ''}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Priority
                  </label>
                  <select
                    {...register('priority')}
                    className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-white focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="HIGH">High</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="LOW">Low</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Status
                  </label>
                  <select
                    {...register('status')}
                    className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-white focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Website
                </label>
                <input
                  {...register('website')}
                  type="url"
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-white focus:ring-2 focus:ring-primary-500"
                  placeholder="https://example.com"
                />
                {errors.website && (
                  <p className="text-red-500 text-sm mt-1">{errors.website.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Twitter Handle
                </label>
                <input
                  {...register('twitter_handle')}
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-white focus:ring-2 focus:ring-primary-500"
                  placeholder="@company"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Description
                </label>
                <textarea
                  {...register('description')}
                  rows={3}
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-white focus:ring-2 focus:ring-primary-500"
                  placeholder="Brief description of the company"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Exclusion Keywords (comma-separated)
                </label>
                <input
                  {...register('exclusions')}
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-white focus:ring-2 focus:ring-primary-500"
                  placeholder="e.g., testnet, game"
                  defaultValue={editingCompany ? formatArrayOutput(editingCompany.exclusions) : ''}
                />
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="submit"
                  disabled={createMutation.isPending || updateMutation.isPending}
                  className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
                >
                  {editingCompany ? 'Update' : 'Create'} Company
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

      {/* Companies List */}
      {isLoading ? (
        <div className="text-center py-8 text-gray-400">Loading companies...</div>
      ) : companies.length === 0 ? (
        <div className="text-center py-8 text-gray-400">
          No companies yet. Add your first company to start monitoring.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {companies.map((company) => (
            <div
              key={company.id}
              className="bg-dark-800 rounded-lg p-4 border border-dark-700 hover:border-primary-500 transition-colors"
            >
              <div className="flex justify-between items-start mb-3">
                <h3 className="text-lg font-semibold text-white">{company.name}</h3>
                <span
                  className={`px-2 py-1 rounded text-xs font-medium ${getPriorityColor(
                    company.priority
                  )}`}
                >
                  {company.priority}
                </span>
              </div>

              {company.tokens.length > 0 && (
                <div className="mb-2">
                  <span className="text-sm text-gray-400">Tokens: </span>
                  <span className="text-sm text-gray-300">
                    {company.tokens.map((t) => `$${t}`).join(', ')}
                  </span>
                </div>
              )}

              {company.twitter_handle && (
                <div className="mb-2 text-sm text-gray-400">
                  Twitter: <span className="text-primary-400">{company.twitter_handle}</span>
                </div>
              )}

              <div className="text-xs text-gray-500 mb-3">
                Added {formatDate(company.created_at)}
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => handleEdit(company)}
                  className="flex-1 px-3 py-1.5 bg-dark-700 text-gray-300 rounded hover:bg-dark-600 transition-colors text-sm"
                >
                  Edit
                </button>
                <button
                  onClick={() => handleDelete(company.id)}
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
