"""boogh food is SnappFood reads and orders."""
import json

from boogh import config


class Food:
    def __init__(self, vault, net, auth):
        self.vault = vault
        self.net = net
        self.auth = auth

    def cities(self, args):
        return self.net.get(f"{config.base}/mobile/v2/area/cities")

    def point(self, args):
        lat = getattr(args, "lat", None) or config.home_lat
        long = getattr(args, "long", None) or config.home_long
        return lat, long

    def area(self, args):
        lat, long = self.point(args)
        return self.net.get(
            f"{config.area}/marketing/api/v1/marketing-area/get-by-location/{lat}/{long}",
            headers={"X-API-KEY": config.area_key})

    def vendors(self, args):
        lat, long = self.point(args)
        params = {"lat": lat, "long": long}
        if args.supertype:
            params["superType"] = args.supertype
        if args.page:
            params["page"] = args.page
        data = self.net.get(f"{config.base}/search/api/v4/restaurant/vendors-list", params)
        if not args.compact:
            return data
        return {"count": data["data"]["count"],
                "vendors": [{"title": v["data"].get("title"),
                             "vendorCode": v["data"].get("vendorCode"),
                             "rate": v["data"].get("rate"),
                             "open": v["data"].get("isOpen")}
                            for v in data["data"]["finalResult"] if v.get("type") == "VENDOR"]}

    def vendor(self, args):
        lat, long = self.point(args)
        return self.net.get(f"{config.apigw}/menu-read-model/vendor-details/{args.code}",
                            {"lat": lat, "long": long})

    def menu(self, args):
        lat, long = self.point(args)
        return self.net.get(f"{config.apigw}/menu-read-model/{args.code}",
                            {"lat": lat, "long": long})

    def reviews(self, args):
        lat, long = self.point(args)
        return self.net.get(f"{config.apigw}/menu-read-model/vendor-review/{args.code}",
                            {"lat": lat, "long": long})

    def place(self, args):
        lat, long = self.point(args)
        return self.net.get(f"{config.base}/map/address/place",
                            {"place": args.place, "lat": lat, "lon": long})

    def reverse(self, args):
        lat, long = self.point(args)
        return self.net.get(f"{config.base}/map/address/reverse",
                            {"lat": lat, "lon": long})

    def profile(self, args):
        return self.net.post(f"{config.base}/mobile/v2/user/load", {},
                             token=self.auth.strict("food", args.token))

    def pending(self, args):
        return self.net.get(f"{config.base}/mobile/v1/order/userPendingOrders",
                            token=self.auth.strict("food", args.token))

    def detail(self, args):
        return self.net.get(f"{config.base}/mobile/v3/order/getOrderDetailData",
                            token=self.auth.strict("food", args.token))

    def rules(self, args):
        return self.net.get(f"{config.base}/customer/order/v1/vendor/{args.code}/min-basket-rules",
                            token=self.auth.strict("food", args.token))

    def body(self, args):
        if args.body_json:
            return json.loads(args.body_json)
        if args.body_file:
            with open(args.body_file) as f:
                return json.load(f)
        raise ValueError("write-body not yet pinned — pass body_json/body_file captured from one web order.")

    def basket_create(self, args):
        return self.auth.guard(args, "food", "POST", f"{config.base}/mobile/v2/basket/",
                               self.body(args), note="creates basket (no charge)")

    def basket_update(self, args):
        return self.auth.guard(args, "food", "PUT", f"{config.base}/mobile/v2/basket/{args.basket_id}",
                               self.body(args), headers={"isBonyan": "true"},
                               note="updates basket (no charge)")

    def basket_delete(self, args):
        return self.auth.guard(args, "food", "DELETE",
                               f"{config.base}/mobile/v2/basket/{args.basket_id}",
                               note="deletes basket")

    def order_new(self, args):
        head = {"Payment-Provider": args.provider} if args.provider else None
        return self.auth.guard(args, "food", "POST", f"{config.base}/mobile/v1/order/new",
                               self.body(args), headers=head,
                               note="PLACES ORDER - may charge. Verify body first!")

    def review_submit(self, args):
        return self.auth.guard(args, "food", "POST",
                               f"{config.base}/mobile/v1/order-review/submit-comment",
                               {"order_id": args.order_id, "comment": args.comment,
                                "rate": args.rate},
                               note="posts public review")
