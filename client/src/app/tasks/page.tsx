"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { createApiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Plus, Edit, Trash2, Check, Clock, AlertCircle, Activity, X, ArrowLeftRight } from "lucide-react";
import { cn } from "@/lib/utils";

const STATUS_COLORS = {
  todo: "bg-blue-100 text-blue-800 border-blue-200",
  in_progress: "bg-yellow-100 text-yellow-800 border-yellow-200",
  done: "bg-green-100 text-green-800 border-green-200",
  cancelled: "bg-red-100 text-red-800 border-red-200",
};

const PRIORITY_COLORS = {
  low: "bg-gray-100 text-gray-800 border-gray-200",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-200",
  high: "bg-red-100 text-red-800 border-red-200",
};

const STATUS_ORDER = ["todo", "in_progress", "done", "cancelled"];

export default function TasksPage() {
  const { data: session, status } = useSession();
  const api = createApiClient((session as any)?.accessToken);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddTask, setShowAddTask] = useState(false);
  const [showEditTask, setShowEditTask] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [newTask, setNewTask] = useState({
    title: "",
    description: "",
    assignee: "",
    deadline: "",
    priority: "medium" as const,
    status: "todo" as const,
  });

  useEffect(() => {
    if (status === "loading") return;
    if (status === "unauthenticated") {
      setLoading(false);
      return;
    }
    loadTasks();
  }, [status]);

  const loadTasks = async () => {
    try {
      const result = await api.listActionItems();
      const organizedTasks = organizeTasks(result);
      setTasks(organizedTasks);
      setLoading(false);
    } catch (error) {
      console.error("Failed to load tasks:", error);
      toast.error("Failed to load tasks");
      setLoading(false);
    }
  };

  const organizeTasks = (tasks) => {
    const organized = {
      todo: [],
      in_progress: [],
      done: [],
      cancelled: [],
    };

    tasks.forEach((task) => {
      const status = task.status || "todo";
      organized[status].push({
        id: task.id,
        title: task.title,
        description: task.description,
        assignee: task.assignee?.name || "Unassigned",
        deadline: task.deadline,
        priority: task.priority || "medium",
        status: status,
        originalData: task,
      });
    });

    return organized;
  };

  const addTask = async () => {
    if (!newTask.title.trim()) {
      toast.error("Task title is required");
      return;
    }

    try {
      const newTaskData = {
        title: newTask.title,
        description: newTask.description,
        assignee: newTask.assignee,
        deadline: newTask.deadline,
        priority: newTask.priority,
        status: newTask.status,
      };

      await api.createActionItem(newTaskData);
      toast.success("Task created successfully");
      setShowAddTask(false);
      setNewTask({
        title: "",
        description: "",
        assignee: "",
        deadline: "",
        priority: "medium",
        status: "todo",
      });
      loadTasks();
    } catch (error) {
      console.error("Failed to create task:", error);
      toast.error("Failed to create task");
    }
  };

  const updateTask = async (taskId, updates) => {
    try {
      await api.updateActionItem(taskId, updates);
      toast.success("Task updated successfully");
      loadTasks();
    } catch (error) {
      console.error("Failed to update task:", error);
      toast.error("Failed to update task");
    }
  };

  const deleteTask = async (taskId) => {
    if (!confirm("Are you sure you want to delete this task?")) {
      return;
    }

    try {
      await api.deleteActionItem(taskId);
      toast.success("Task deleted successfully");
      loadTasks();
    } catch (error) {
      console.error("Failed to delete task:", error);
      toast.error("Failed to delete task");
    }
  };

  const moveTask = async (taskId, fromStatus, toStatus) => {
    try {
      await updateTask(taskId, { status: toStatus });
      toast.success(`Task moved to ${toStatus}`);
    } catch (error) {
      console.error("Failed to move task:", error);
      toast.error("Failed to move task");
    }
  };

  const getStatusColor = (status) => {
    return STATUS_COLORS[status] || STATUS_COLORS.todo;
  };

  const getPriorityColor = (priority) => {
    return PRIORITY_COLORS[priority] || PRIORITY_COLORS.medium;
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "todo":
        return <Clock className="w-3 h-3" />;
      case "in_progress":
        return <Activity className="w-3 h-3 animate-pulse" />;
      case "done":
        return <Check className="w-3 h-3" />;
      case "cancelled":
        return <X className="w-3 h-3" />;
      default:
        return <Clock className="w-3 h-3" />;
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return "No deadline";
    const date = new Date(dateString);
    return date.toLocaleDateString();
  };

  const getStatusLabel = (status) => {
    const labels = {
      todo: "To Do",
      in_progress: "In Progress",
      done: "Done",
      cancelled: "Cancelled",
    };
    return labels[status] || "Unknown";
  };

  const getPriorityLabel = (priority) => {
    const labels = {
      low: "Low",
      medium: "Medium",
      high: "High",
    };
    return labels[priority] || "Medium";
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background p-6">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
        </div>
      </div>
    );
  }

  if (status === "unauthenticated") {
    return (
      <div className="min-h-screen bg-background p-6">
        <div className="text-center">
          <p className="text-muted-foreground">
            Please <a href="/auth/login" className="text-primary hover:underline">
              log in
            </a> to view your tasks.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Task Management</h1>
            <p className="text-sm text-muted-foreground">
              Manage and track your action items across different statuses
            </p>
          </div>
          <Button 
            onClick={() => setShowAddTask(true)}
            leftIcon={<Plus className="w-4 h-4" />}
            variant="outline"
          >
            Add Task
          </Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {STATUS_ORDER.map((status) => (
            <div key={status} className="bg-card rounded-xl border p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-foreground">
                  {getStatusLabel(status)}
                </h2>
                <Badge variant="secondary" className={getStatusColor(status)}>
                  {tasks[status]?.length || 0}
                </Badge>
              </div>

              <div className="space-y-3">
                {tasks[status]?.map((task) => (
                  <Card key={task.id} className="relative group">
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm font-medium">
                          {task.title}
                        </CardTitle>
                        <div className="flex items-center gap-1">
                          <Badge variant="secondary" className={getPriorityColor(task.priority)}>
                            {getPriorityLabel(task.priority)}
                          </Badge>
                        </div>
                      </div>
                      <CardDescription className="text-xs text-muted-foreground mt-1">
                        {task.description?.substring(0, 50)}...
                      </CardDescription>
                    </CardHeader>

                    <CardContent className="pt-0">
                      <div className="flex items-center justify-between text-xs text-muted-foreground mt-2">
                        <div className="flex items-center gap-1">
                          {getStatusIcon(task.status)}
                          <span>{task.assignee}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <span>{formatDate(task.deadline)}</span>
                        </div>
                      </div>

                      <div className="mt-3 flex items-center justify-between">
                        <div className="flex items-center gap-1">
                          <Badge variant="secondary" className={getStatusColor(task.status)}>
                            {getStatusLabel(task.status)}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditingTask(task);
                              setShowEditTask(true);
                            }}
                            className="group-hover:block"
                          >
                            <Edit className="w-3 h-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteTask(task.id);
                            }}
                            className="group-hover:block"
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        </div>
                      </div>
                    </CardContent>

                    <div className="absolute -top-2 -right-2 w-8 h-8 bg-primary text-primary-foreground rounded-full flex items-center justify-center group-hover:block hidden">
                      <ArrowLeftRight className="w-4 h-4" />
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <Dialog open={showAddTask} onOpenChange={setShowAddTask}>
        <DialogContent className="sm:w-96">
          <DialogHeader>
            <DialogTitle>Add New Task</DialogTitle>
          </DialogHeader>
          <DialogDescription>
            Create a new task with all required details
          </DialogDescription>
          <div className="space-y-4 mt-4">
            <div>
              <Label htmlFor="title" className="required">
                Title
              </Label>
              <Input
                id="title"
                value={newTask.title}
                onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                placeholder="Enter task title"
              />
            </div>
            <div>
              <Label htmlFor="description">Description</Label>
              <textarea
                id="description"
                value={newTask.description}
                onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                placeholder="Enter task description"
                rows={3}
                className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium outline-none focus:bg-background focus:ring-1 focus:ring-ring focus:border-transparent disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>
            <div>
              <Label htmlFor="assignee">Assignee</Label>
              <Input
                id="assignee"
                value={newTask.assignee}
                onChange={(e) => setNewTask({ ...newTask, assignee: e.target.value })}
                placeholder="Enter assignee name"
              />
            </div>
            <div>
              <Label htmlFor="deadline">Deadline</Label>
              <Input
                id="deadline"
                type="date"
                value={newTask.deadline}
                onChange={(e) => setNewTask({ ...newTask, deadline: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="priority">Priority</Label>
              <Select
                id="priority"
                value={newTask.priority}
                onValueChange={(value) => setNewTask({ ...newTask, priority: value as any })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="status">Status</Label>
              <Select
                id="status"
                value={newTask.status}
                onValueChange={(value) => setNewTask({ ...newTask, status: value as any })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todo">To Do</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="done">Done</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="mt-4 flex gap-2 pt-2">
            <Button onClick={() => setShowAddTask(false)}>Cancel</Button>
            <Button onClick={addTask} variant="default" className="bg-primary">
              Add Task
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={showEditTask} onOpenChange={setShowEditTask}>
        <DialogContent className="sm:w-96">
          <DialogHeader>
            <DialogTitle>Edit Task</DialogTitle>
          </DialogHeader>
          <DialogDescription>
            Update task details
          </DialogDescription>
          <div className="space-y-4 mt-4">
            <div>
              <Label htmlFor="editTitle" className="required">
                Title
              </Label>
              <Input
                id="editTitle"
                value={editingTask?.title || ""}
                onChange={(e) => setEditingTask({ ...editingTask, title: e.target.value })}
                placeholder="Enter task title"
              />
            </div>
            <div>
              <Label htmlFor="editDescription">Description</Label>
              <textarea
                id="editDescription"
                value={editingTask?.description || ""}
                onChange={(e) => setEditingTask({ ...editingTask, description: e.target.value })}
                placeholder="Enter task description"
                rows={3}
                className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium outline-none focus:bg-background focus:ring-1 focus:ring-ring focus:border-transparent disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>
            <div>
              <Label htmlFor="editAssignee">Assignee</Label>
              <Input
                id="editAssignee"
                value={editingTask?.assignee || ""}
                onChange={(e) => setEditingTask({ ...editingTask, assignee: e.target.value })}
                placeholder="Enter assignee name"
              />
            </div>
            <div>
              <Label htmlFor="editDeadline">Deadline</Label>
              <Input
                id="editDeadline"
                type="date"
                value={editingTask?.deadline || ""}
                onChange={(e) => setEditingTask({ ...editingTask, deadline: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="editPriority">Priority</Label>
              <Select
                id="editPriority"
                value={editingTask?.priority || "medium"}
                onValueChange={(value) => setEditingTask({ ...editingTask, priority: value as any })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="editStatus">Status</Label>
              <Select
                id="editStatus"
                value={editingTask?.status || "todo"}
                onValueChange={(value) => setEditingTask({ ...editingTask, status: value as any })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todo">To Do</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="done">Done</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="mt-4 flex gap-2 pt-2">
            <Button onClick={() => setShowEditTask(false)}>Cancel</Button>
            <Button
              onClick={() => {
                if (editingTask) {
                  updateTask(editingTask.id, {
                    title: editingTask.title,
                    description: editingTask.description,
                    assignee: editingTask.assignee,
                    deadline: editingTask.deadline,
                    priority: editingTask.priority,
                    status: editingTask.status,
                  });
                  setShowEditTask(false);
                }
              }}
              variant="default"
              className="bg-primary"
            >
              Update Task
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}