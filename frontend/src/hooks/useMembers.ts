/**
 * 組織の管理者のメンバーの一覧と作成（I620）
 * キーに見ている人を入れる（別の人に替わったとき前の人の一覧を見せない・規約 §5）
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { memberService } from '../services/member.service';
import { toLoadState } from './queryLoadState';

export const membersKeyRoot = (viewerId: string) => ['members', viewerId] as const;

export const useMembers = (viewerId: string, page: number) => {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: [...membersKeyRoot(viewerId), page],
    queryFn: () => memberService.list(page),
  });

  const create = useMutation({
    mutationFn: (userId: string) => memberService.create(userId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: membersKeyRoot(viewerId) }),
  });

  return { list: toLoadState(query), create };
};
