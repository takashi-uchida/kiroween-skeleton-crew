#!/usr/bin/env python3
"""
Kubernetes Runner Example

このサンプルは、Kubernetes JobとしてAgent Runnerを実行する方法を示します。
"""

from pathlib import Path
from necrocode.agent_runner import (
    TaskContext,
    KubernetesRunner,
    RunnerConfig,
    ExecutionMode
)


def main():
    """Kubernetes JobとしてAgent Runnerを実行する例"""
    
    print("=== Kubernetes Runner Example ===")
    print()
    
    # 1. タスクコンテキストを作成
    print("=== タスクコンテキストの作成 ===")
    task_context = TaskContext(
        task_id="4.1",
        spec_name="chat-app",
        title="チャットUIの実装",
        description="Reactを使用したチャットインターフェースを実装",
        acceptance_criteria=[
            "メッセージ一覧が表示される",
            "メッセージを送信できる",
            "リアルタイムでメッセージが更新される",
            "ユーザー名が表示される"
        ],
        dependencies=["3.1"],
        required_skill="frontend",
        slot_path=Path("/workspace"),  # Pod内のパス
        slot_id="slot-1",
        branch_name="feature/task-4.1-chat-ui",
        test_commands=["npm test -- --run"],
        timeout_seconds=1800
    )
    
    print(f"タスクID: {task_context.task_id}")
    print(f"タイトル: {task_context.title}")
    print()
    
    # 2. Kubernetes Runner設定を作成
    print("=== Kubernetes Runner設定の作成 ===")
    config = RunnerConfig(
        execution_mode=ExecutionMode.KUBERNETES,
        default_timeout_seconds=1800,
        log_level="INFO",
        
        # Kubernetes固有の設定
        k8s_namespace="necrocode",
        k8s_image="necrocode/agent-runner:latest",
        k8s_image_pull_policy="Always",
        k8s_service_account="agent-runner",
        k8s_secrets=["git-token", "artifact-store-credentials"],
        k8s_config_maps=["runner-config"],
        k8s_resources={
            "requests": {
                "memory": "1Gi",
                "cpu": "1000m"
            },
            "limits": {
                "memory": "2Gi",
                "cpu": "2000m"
            }
        },
        k8s_node_selector={
            "workload": "agent-runner"
        },
        k8s_tolerations=[
            {
                "key": "dedicated",
                "operator": "Equal",
                "value": "agent-runner",
                "effect": "NoSchedule"
            }
        ]
    )
    
    print(f"Namespace: {config.k8s_namespace}")
    print(f"イメージ: {config.k8s_image}")
    print(f"リソース: {config.k8s_resources}")
    print()
    
    # 3. Kubernetes Runnerを作成
    print("=== Kubernetes Runnerの作成 ===")
    runner = KubernetesRunner(config)
    print(f"Runner ID: {runner.runner_id}")
    print(f"実行モード: {runner.execution_mode}")
    print()
    
    # 4. タスクを実行
    print("=== タスクの実行 ===")
    print("Kubernetes Jobを作成してタスクを実行中...")
    print()
    
    try:
        result = runner.run(task_context)
        
        # 5. 結果を表示
        print("=== 実行結果 ===")
        print(f"成功: {result.success}")
        print(f"実行時間: {result.duration_seconds:.2f}秒")
        
        if result.success:
            print(f"\nJob名: {runner.job_name}")
            print(f"成果物数: {len(result.artifacts)}")
            
            print("\n成果物:")
            for artifact in result.artifacts:
                print(f"  - {artifact.type}: {artifact.uri}")
            
            if result.impl_result:
                print(f"\n実装結果:")
                print(f"  - 変更ファイル: {', '.join(result.impl_result.files_changed)}")
            
            if result.test_result:
                print(f"\nテスト結果:")
                print(f"  - 成功: {result.test_result.success}")
                for test in result.test_result.test_results:
                    status = "✓" if test.success else "✗"
                    print(f"    {status} {test.command}")
        else:
            print(f"\nエラー: {result.error}")
    
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


def demonstrate_job_manifest():
    """Kubernetes Jobマニフェストの例"""
    
    print("\n=== Kubernetes Jobマニフェスト ===")
    print()
    
    # Jobマニフェストの内容
    manifest_content = """
apiVersion: batch/v1
kind: Job
metadata:
  name: agent-runner-task-4-1
  namespace: necrocode
  labels:
    app: agent-runner
    task-id: "4.1"
    spec-name: chat-app
spec:
  ttlSecondsAfterFinished: 3600
  backoffLimit: 3
  template:
    metadata:
      labels:
        app: agent-runner
        task-id: "4.1"
    spec:
      serviceAccountName: agent-runner
      restartPolicy: Never
      
      # ノードセレクター
      nodeSelector:
        workload: agent-runner
      
      # Toleration
      tolerations:
        - key: dedicated
          operator: Equal
          value: agent-runner
          effect: NoSchedule
      
      # ボリューム
      volumes:
        - name: workspace
          emptyDir: {}
        - name: git-token
          secret:
            secretName: git-token
        - name: runner-config
          configMap:
            name: runner-config
      
      containers:
        - name: agent-runner
          image: necrocode/agent-runner:latest
          imagePullPolicy: Always
          
          # リソース制限
          resources:
            requests:
              memory: "1Gi"
              cpu: "1000m"
            limits:
              memory: "2Gi"
              cpu: "2000m"
          
          # 環境変数
          env:
            - name: TASK_ID
              value: "4.1"
            - name: SPEC_NAME
              value: "chat-app"
            - name: GIT_TOKEN
              valueFrom:
                secretKeyRef:
                  name: git-token
                  key: token
            - name: LOG_LEVEL
              value: "INFO"
          
          # ボリュームマウント
          volumeMounts:
            - name: workspace
              mountPath: /workspace
            - name: git-token
              mountPath: /secrets/git
              readOnly: true
            - name: runner-config
              mountPath: /config
              readOnly: true
          
          # ヘルスチェック
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
          
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
"""
    
    print("job.yaml:")
    print(manifest_content)
    print()
    
    print("適用コマンド:")
    print("  kubectl apply -f job.yaml")
    print()
    
    print("ステータス確認:")
    print("  kubectl get job agent-runner-task-4-1 -n necrocode")
    print()
    
    print("ログ確認:")
    print("  kubectl logs -f job/agent-runner-task-4-1 -n necrocode")


def demonstrate_secret_configmap():
    """SecretとConfigMapの例"""
    
    print("\n=== Secret と ConfigMap ===")
    print()
    
    # Secretの内容
    secret_content = """
apiVersion: v1
kind: Secret
metadata:
  name: git-token
  namespace: necrocode
type: Opaque
stringData:
  token: ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
"""
    
    print("secret.yaml:")
    print(secret_content)
    print()
    
    # ConfigMapの内容
    configmap_content = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: runner-config
  namespace: necrocode
data:
  config.yaml: |
    execution_mode: kubernetes
    default_timeout_seconds: 1800
    git_retry_count: 3
    log_level: INFO
    artifact_store_url: http://artifact-store.necrocode.svc.cluster.local:8080
"""
    
    print("configmap.yaml:")
    print(configmap_content)
    print()
    
    print("適用コマンド:")
    print("  kubectl apply -f secret.yaml")
    print("  kubectl apply -f configmap.yaml")


def demonstrate_service_account():
    """ServiceAccountの例"""
    
    print("\n=== ServiceAccount ===")
    print()
    
    # ServiceAccountの内容
    sa_content = """
apiVersion: v1
kind: ServiceAccount
metadata:
  name: agent-runner
  namespace: necrocode
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: agent-runner
  namespace: necrocode
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/log"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["batch"]
    resources: ["jobs"]
    verbs: ["get", "list", "watch", "create", "update", "patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: agent-runner
  namespace: necrocode
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: agent-runner
subjects:
  - kind: ServiceAccount
    name: agent-runner
    namespace: necrocode
"""
    
    print("serviceaccount.yaml:")
    print(sa_content)
    print()
    
    print("適用コマンド:")
    print("  kubectl apply -f serviceaccount.yaml")


if __name__ == "__main__":
    main()
    # demonstrate_job_manifest()
    # demonstrate_secret_configmap()
    # demonstrate_service_account()
