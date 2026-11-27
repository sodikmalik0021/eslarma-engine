import subprocess, torch, time
print(subprocess.run(["nvidia-smi"], capture_output=True, text=True).stdout)
print("cuda", torch.cuda.is_available(), torch.cuda.device_count(), [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())])
t = time.time(); a = torch.randn(4096, 4096, device="cuda"); [a @ a for _ in range(50)]; torch.cuda.synchronize(); print("matmul s", round(time.time() - t, 2))
open("/kaggle/working/ok.txt", "w").write("gpu ok")
